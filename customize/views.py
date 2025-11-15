from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
# from .forms import PersonalizedBottleForm

def customize_bottle_view(request):
    pass
    # if request.method == 'POST':
    #     form = PersonalizedBottleForm(request.POST, request.FILES)
    #     if form.is_valid():
    #         form.save()
    #         return render(request, 'home.html')
    # else:
    #     form = PersonalizedBottleForm()

    # return render(request, 'home.html')
