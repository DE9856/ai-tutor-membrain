from supabase_client import supabase


# -------------------------
# SIGN UP
# -------------------------
def signup_user(email: str, password: str):
    try:
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })

        return {
            "status": "success",
            "user_id": response.user.id,
            "access_token": response.session.access_token
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# -------------------------
# LOGIN
# -------------------------
def login_user(email: str, password: str):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        return {
            "status": "success",
            "user_id": response.user.id,
            "access_token": response.session.access_token
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }