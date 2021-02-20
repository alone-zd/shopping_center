# 自定义用户认证后端：实现多账号登陆
from django.contrib.auth.backends import ModelBackend
import re
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from django.conf import settings
from itsdangerous import BadData

from users.models import User
from . import constants


def check_verify_email_token(token):
    """
    反序列化token，获取到user
    :param token: 序列化后用户信息
    :return: user
    """
    s = Serializer(settings.SECRET_KEY, constants.VERIFY_EMAIL_TOKEN_EXPIRES)
    try:
        data = s.loads(token)
    except BadData:
        return None
    else:
        user_id = data.get('user_id')
        email = data.get('email')
        try:
            user = User.objects.get(id=user_id, email=email)
        except User.DoesNotExist:
            return None
        else:
            return user
    

def generate_verify_email_url(user):
    """
    商城邮箱激活连接
    :param user: 当前登陆用户
    :return: token
    """
    s = Serializer(settings.SECRET_KEY, constants.VERIFY_EMAIL_TOKEN_EXPIRES)
    data = {'user_id': user.id, 'email': user.email}
    token = s.dumps(data)

    return settings.EMAIL_VERIFY_URL + '?token=' + token.decode()

def get_user_by_account(account):
    """
    通过账户获取用户
    :param account: 用户名或手机号
    :return: user
    """
    try:
        if re.match(r'1[3-9]\d{9}$', account):
            user = User.objects.get(mobile=account)
        else:
            user = User.objects.get(username=account)
    except User.DoesNotExist:
        return None
    else:
        return user

class UsernameMobileBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        重写用户认证的方法
        :param username: 用户名或手机号
        :param password: 密码明文
        :param kwargs: 额外参数
        :return: user
        """
        user = get_user_by_account(username)
        if user and user.check_password(password):
            return user
        else:
            return None

