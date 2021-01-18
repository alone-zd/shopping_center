from django.shortcuts import render, redirect
from django.views import View
from django import http
import re
from users.models import User
from django.db import DatabaseError
from django.urls import reverse
from django.contrib.auth import login
from xiaoy_malls.utils.response_code import RETCODE
# Create your views here.


class UsernameCountView(View):

    def get(self, request, username):
        """
        获取当前用户名在数据库中存在的次数
        ：params username：用户名
        ：return Json
        """
        count = User.objects.filter(username=username).count()
        return http.JsonResponse({"code": RETCODE.OK, "msg": "ok", "count": count})

class MobileCountView(View):
    
    def get(self, request, mobile):
        """
        获取当前手机号在数据库中存在的次数
        :params mobile：手机号
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
        if allow != 'on':
            return http.HttpResponseForbidden('请勾选用户协议')
        # 业务代码
        try:
            user = User.objects.create_user(username=username, password=password, mobile=mobile)
        except DatabaseError:
            return render(request, 'register.html', {'register_errmsg': '注册失败'})
        # 状态保持
        login(request, user)
        return redirect(reverse('contents:index'))




