from django.shortcuts import render, HttpResponse
from django.views import View
from django.urls import reverse
from collections import OrderedDict

from goods.models import GoodsChannelGroup, GoodsChannel, GoodsCategory
# Create your views here.


class IndexView(View):
    def get(self, request):
        """提供首页广告页面"""
        categories = OrderedDict()
        channels = GoodsChannel.objects.order_by('group_id', 'sequence')
        for channel in channels:
            # 获取当前频道所在组
            group_id = channel.group_id
            if group_id not in categories:
                categories[group_id] = {'channels': [], 'sub_cats': []}

            # 查询当前频道对应的一级类别
            cat1 = channel.category
            categories[group_id]['channels'].append({
                'id': cat1.id,
                'name': cat1.name,
                'url': channel.url
            })
            # 查询二级和三级类别
            for cat2 in cat1.subs.all():
                cat2.sub_cats = []
                for cat3 in cat2.subs.all():
                    cat2.sub_cats.append(cat3)

                categories[group_id]['sub_cats'].append(cat2)

        context = {
            'categories': categories
        }
        return render(request, 'index.html', context=context)
