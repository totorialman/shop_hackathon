from django.shortcuts import render

# Create your views here.
def main(request):
    
    return render(request, 'main.html')

def product1(request):

    return render(request, 'product1.html')