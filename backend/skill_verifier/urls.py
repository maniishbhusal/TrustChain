from django.urls import path
from .views import VerifySkillsView, GetVerificationView

urlpatterns = [
    path('verify-skills/', VerifySkillsView.as_view(), name='verify_skills'),
    path('verification/<int:verification_id>/', GetVerificationView.as_view(), name='get_verification'),
]