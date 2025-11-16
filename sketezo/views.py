from django.shortcuts import render

# main branch
# new branch 
def home(request):
    return render(request,'home/skatezo_development.html')

def abhout(request):
    return render(request,'about.html')