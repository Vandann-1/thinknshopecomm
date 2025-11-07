from django.shortcuts import render
# views.py


def dev_notice(request):
    return render(request, "dev_mode/dev_notice.html")
