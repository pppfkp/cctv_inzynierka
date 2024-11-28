from django.urls import path
from .views import AddUserAPIView, FindClosestEmbeddingView, UploadEmbeddingView, UploadBulkEmbeddingsView, DeleteAllEmbeddingsView, DeleteEmbeddingView, UserListView

urlpatterns = [
    path('find-closest-embedding/', FindClosestEmbeddingView.as_view(), name='find_closest_embedding'),
    path('upload-embedding/', UploadEmbeddingView.as_view(), name='upload_embedding'),
    path('upload-bulk-embeddings/', UploadBulkEmbeddingsView.as_view(), name='upload_bulk_embeddings'),
    path('delete-embedding/<int:embedding_id>/', DeleteEmbeddingView.as_view(), name='delete_embedding'),
    path('delete-all-embeddings/', DeleteAllEmbeddingsView.as_view(), name='delete_all_embeddings'), 
    path('users/', UserListView.as_view(), name='user-list'),           # For all users
    path('users/<int:user_id>/', UserListView.as_view(), name='user-detail'),  # For a specific user 
    path("users/add-user/", AddUserAPIView.as_view(), name="add_user"),
]