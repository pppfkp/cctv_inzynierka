from django.urls import path
from .views import FindClosestEmbeddingView, UploadEmbeddingView, UploadBulkEmbeddingsView, DeleteAllEmbeddingsView, DeleteEmbeddingView

urlpatterns = [
    path('find-closest-embedding/', FindClosestEmbeddingView.as_view(), name='find_closest_embedding'),
    path('upload-embedding/', UploadEmbeddingView.as_view(), name='upload_embedding'),
    path('upload-bulk-embeddings/', UploadBulkEmbeddingsView.as_view(), name='upload_bulk_embeddings'),
    path('delete-embedding/<int:embedding_id>/', DeleteEmbeddingView.as_view(), name='delete_embedding'),
    path('delete-all-embeddings/', DeleteAllEmbeddingsView.as_view(), name='delete_all_embeddings'),  
]