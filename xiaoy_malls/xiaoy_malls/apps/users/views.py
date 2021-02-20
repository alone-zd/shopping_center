from django.shortcuts import render, redirect
from django.views import View
from django import http
import re, json, logging
from django.db import DatabaseError
from django.urls import reverse
from django.contrib.auth import login, authenticate, logout
from django_redis import get_redis_connection
from django.contrib.auth.mixins import LoginRequiredMixin

from users.models import User
from xiaoy_malls.utils.response_code import RETCODE
from xiaoy_malls.utils.views import LoginRequiredJSONMixin
from celery_tasks.email.tasks import send_verify_email
from users.utils import generate_verify_email_url, check_verify_email_token
# Create your views here.


logger = logging.getLogger('django')


class AddressView(LoginRequiredMixin, View):
    """用户收货地址"""

    def get(self, request):
        return render(request, 'user_center_site.html')


class VerifyEmailView(View):
    """验证"""
    
    def get(self, request):
        token = request.GET.get('token')
        if not token:
            return http.HttpResponseForbidden('缺少token')
        user = check_verify_email_token(token)
        if not user:
            return http.HttpResponseBadRequest('无效token')
        try:
            user.email_active = True
            user.save()
        except Exception as e:
            logger.error(e)
            return http.HttpResponseServerError('激活邮箱失败')
        
        return redirect(reverse('users:info'))



class EmailView(LoginRequiredJSONMixin, View):
    """添加邮箱"""

    def put(self, request):
        json_str = request.body.decode()
        json_dict = json.loads(json_str)
        email = json_dict.get('email')

        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return http.HttpResponseForbidden('参数email有误')
        # 给当前登陆用户绑定email字段
        try:
            request.user.email = email
            request.user.save()
        except Exception as e:
            logger.error(e)
            return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '添加邮箱失败'})
        # 发送邮箱验证邮件
        verify_url = generate_verify_email_url(request.user)
        print(verify_url)
        send_verify_email.delay(email, verify_url)
        return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK'})


class UserInfoView(LoginRequiredMixin, View):
    """用户中心"""

    def get(self,request):
        """提供用户中心页面"""
        context = {
            'username': request.user.username,
            'mobile': request.user.mobile,
            'email': request.user.email,
            'email_active': request.user.email_active
        }
        return render(request, 'user_center_info.html', context=context)


class LogoutView(View):

    def get(self, request):
        """用户推出登陆"""
        logout(request)
        response = redirect(reverse('contents:index'))
        response.delete_cookie('username')
        return response


class LoginView(View):
    """用户登陆"""
    def get(self, request):
        """提供用户登陆页面"""
        return render(request, 'login.html')

    def post(self, request):
        """实现用户登陆逻辑"""
        username = request.POST.get("username")
        password = request.POST.get('password')
        remembered = request.POST.get('remembered')

        if not all([username, password]):
            return http.HttpResponseForbidden('缺少必传参数')    

        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden("请输入5-20字符的用户名")
        if not re.match(r'^[0-9a-zA-Z]{8,20}$', password):
            return http.HttpResponseForbidden("请输入8-20字符的密码")

        user = authenticate(username=username, password=password)
        if user is None:
            return render(request, 'login.html', {'account_errmsg': '账号或密码错误'})
        # 状态保持
        login(request, user)
        if remembered != 'on':
            # 未记住登陆，状态保持在浏览器会话结束后销毁
            request.session.set_expiry(0)
        else:
            # 保持默认两周
            request.session.set_expiry(None)

        next_url = request.GET.get('next')
        if next_url:
            response = redirect(next_url)
        else:
            response = redirect(reverse('contents:index'))
       
        # 首页展示用户名信息，将用户名缓存在cookie中
        response.set_cookie('username', user.username, max_age=3600 * 24 * 15)
        
        return response




class UsernameCountView(View):

    def get(self, request, username):
        """
        获取当前用户名在数据库中存在的次数
        :param username：用户名
        :return Json
        """
        count = User.objects.filter(username=username).count()
        return http.JsonResponse({"code": RETCODE.OK, "msg": "ok", "count": count})

class MobileCountView(View):
    
    def get(self, request, mobile):
        """
        获取当前手机号在数据库中存在的次数
        :param mobile：手机号
        :return: Json
        """
        count = User.objects.filter(mobile=mobile).count()
        return http.JsonResponse({"code": RETCODE.OK, "msg": "ok", "count": count})


class RegisterView(View):

    def get(self, request):
        """
        提供注册界面
        :param request: 请求对象
        :return: 注册界面
        """
        return render(request, 'register.html')

    def post(self, request):
        """
        实现用户注册
        :param request: 请求对象
        :return: 注册结果
        """
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        mobile = request.POST.get('mobile')
        sms_code_client = request.POST.get('sms_code')
        allow = request.POST.get('allow')

        # 参数校验
        if not all([username, password, password2, mobile, allow]):
            return http.HttpResponseForbidden("缺少必传参数")

        if not re.match(r'^[a-zA-Z0-9_-]{5,20}$', username):
            return http.HttpResponseForbidden("请输入5-20字符的用户名")
        if not re.match(r'^[0-9a-zA-Z]{8,20}$', password):
            return http.HttpResponseForbidden("请输入8-20字符的密码")
        if password != password2:
            return http.HttpResponseForbidden('两次输入的密码不一致')
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return http.HttpResponseForbidden('请输入正确的手机号码')
        
        # 短信验证码
        redis_con = get_redis_connection('verify_code')
        sms_code_server = redis_con.get('sms_%s' % mobile)
        if sms_code_server is None:
            return render(request, 'register.html', {'sms_code_errmsg': '短信验证码已失效'})
        if sms_code_client != sms_code_server.decode():
            return render(request, 'register.html', {'sms_code_errmsg': '输入短信验证码有误'})
        
        if allow != 'on':
            return http.HttpResponseForbidden('请勾选用户协议')
        # 业务代码
        try:
            user = User.objects.create_user(username=username, password=password, mobile=mobile)
        except DatabaseError:
            return render(request, 'register.html', {'register_errmsg': '注册失败'})
        # 状态保持
        login(request, user)
        # 将用户名写入到cookie中
        response = redirect(reverse('contents:index'))
        response.set_cookie('username', user.username, max_age=3600 * 24 * 15)
    
        return response




