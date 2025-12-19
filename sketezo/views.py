from django.shortcuts import render

# main branch
# new branch 
def home(request):
    return render(request,'home/skatezo_development.html')

def abhout(request):
    return render(request,'supports/about.html')

def shipping(request):
    return render(request,'supports/shipping.html')

def contact(request):
    return render(request,'supports/contact.html')

def terms(request):
    return render(request,'supports/terms.html')

def policy(request):
    return render(request,'supports/policy.html')
