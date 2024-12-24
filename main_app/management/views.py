from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt  # Disable CSRF for this endpoint 
def login_view(request):
    if request.method == "POST":
        try:
            # Parse the JSON body
            data = json.loads(request.body)
            username = data.get("username")
            password = data.get("password")

            # Authenticate user
            user = authenticate(request, username=username, password=password)
            if user is not None:
                # Log the user in
                login(request, user)
                return JsonResponse({"message": "Login successful"}, status=200)
            else:
                return JsonResponse({"error": "Invalid credentials"}, status=401)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    else:
        return JsonResponse({"error": "Invalid request method"}, status=405)
    

@csrf_exempt  # Disable CSRF for this endpoint 
def logout_view(request):
    if request.method == "POST":
        # Log the user out
        logout(request)
        return JsonResponse({"message": "Logout successful"}, status=200)
    else:
        return JsonResponse({"error": "Invalid request method. Use POST."}, status=405)

