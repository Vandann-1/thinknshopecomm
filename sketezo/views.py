from django.shortcuts import render

# main branch
# new branch 
def home(request):
    return render(request,'home/skatezo_development.html')