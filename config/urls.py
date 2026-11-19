from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from polls import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("polls/create/", views.create_poll, name="create_poll"),
    path("polls/<int:poll_id>/", views.poll_detail, name="poll_detail"),
    path("polls/<int:poll_id>/vote/", views.vote, name="vote"),
    path("polls/<int:poll_id>/results/", views.results, name="results"),
    path("my-polls/", views.my_polls, name="my_polls"),
    path("u/<str:username>/", views.profile, name="profile"),
    path("u/<str:username>/follow/", views.follow_user, name="follow_user"),
    path("polls/<int:poll_id>/like/", views.like_poll, name="like_poll"),
    path("polls/<int:poll_id>/comment/", views.add_comment, name="add_comment"),
    path("comments/<int:comment_id>/delete/", views.delete_comment, name="delete_comment"),
    path("posts/create/", views.create_social_post, name="create_social_post"),
    path("posts/<int:post_id>/", views.social_post_detail, name="social_post_detail"),
    path("posts/<int:post_id>/like/", views.like_social_post, name="like_social_post"),
    path("posts/<int:post_id>/comment/", views.comment_social_post, name="comment_social_post"),
    path("messages/", views.message_inbox, name="message_inbox"),
    path("messages/start/<str:username>/", views.start_conversation, name="start_conversation"),
    path("messages/<int:conversation_id>/", views.conversation_detail, name="conversation_detail"),
    path("messages/<int:conversation_id>/updates/", views.message_updates, name="message_updates"),
    path("share/<uuid:token>/like/", views.like_poll, name="shared_like"),
    path("share/<uuid:token>/comment/", views.add_comment, name="shared_comment"),
    path("share/<uuid:token>/", views.shared_poll, name="shared_poll"),
    path("share/<uuid:token>/vote/", views.vote, name="shared_vote"),
    path("share/<uuid:token>/results/", views.shared_results, name="shared_results"),
]
