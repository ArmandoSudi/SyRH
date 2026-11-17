def request_author(request):
    """The signed-in user of a request, or None for an anonymous one."""
    user = getattr(request, "user", None)
    return user if user is not None and user.is_authenticated else None


class AuthorMixin:
    """DRF viewset mixin that stamps BaseModel rows with the signed-in user.

    The same user becomes the author of the audit entry, deletion included.

    Usage: class SiteViewSet(AuthorMixin, viewsets.ModelViewSet). It grants no
    access: the view keeps its own permission classes.
    """

    def perform_create(self, serializer):
        author = request_author(self.request)
        serializer.save(cree_par=author, modifie_par=author)

    def perform_update(self, serializer):
        serializer.save(modifie_par=request_author(self.request))

    def perform_destroy(self, instance):
        instance.delete(auteur=request_author(self.request))
