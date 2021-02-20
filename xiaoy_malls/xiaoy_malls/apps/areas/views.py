from django.shortcuts import render
from django.views import View
from django import http
import logging
from django.core.cache import cache

from areas.models import Area
from xiaoy_malls.utils.response_code import RETCODE
# Create your views here.


logger = logging.getLogger('django')

class AreasView(View):
    """省市区三级联动"""
    
    def get(self, request):
        # 判断当前查询数据是省份/市区
        area_id = request.GET.get('area_id')
        if not area_id:
            province_list = cache.get('province_list')
            if not province_list:
                try:
                    # 省级
                    province_model_list = Area.objects.filter(parent__isnull=True)
                    province_list = []
                    for province_model in province_model_list:
                        province_dict = {
                            "id": province_model.id,
                            "name": province_model.name
                        }
                        province_list.append(province_dict)
                    # 缓存省份列表数据
                    cache.set('province_list', province_list, 3600)

                except Exception as e:
                    logger.error(e)
                    return http.JsonResponse({'code': RETCODE.OK, 'errmsg': '查询省份数据错误'})
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'province_list': province_list})
        else:
            # 市区
            sub_data = cache.get('sub_area_'+ area_id)
            if not sub_data:
                try:
                    parent_model = Area.objects.get(id=area_id)  # 查询市或区的父级
                    sub_model_list = parent_model.subs.all()

                    # 序列化市或区数据
                    sub_list = []
                    for sub_model in sub_model_list:
                        sub_list.append({'id': sub_model.id, 'name': sub_model.name})

                    sub_data = {
                        'id': parent_model.id,  # 父级pk
                        'name': parent_model.name,  # 父级name
                        'subs': sub_list  # 父级的子集
                    }
                    cache.set('sub_area_'+ area_id, sub_data, 3600)
                except Exception as e:
                    logger.error(e)
                    return http.JsonResponse({'code': RETCODE.DBERR, 'errmsg': '城市或区数据错误'})
            return http.JsonResponse({'code': RETCODE.OK, 'errmsg': 'OK', 'sub_data': sub_data})
