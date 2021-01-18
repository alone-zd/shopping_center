from django.shortcuts import render, HttpResponse
from django.views import View
from django.urls import reverse
# Create your views here.


class IndexView(View):
    def get(self, request):

        return render(request, 'index.html')
