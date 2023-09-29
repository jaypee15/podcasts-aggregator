
from django.views.generic import ListView
from django.db.models import Q

from .models import Episode

class HomePageView(ListView):
    template_name = "home.html"
    paginate_by = 10
    model = Episode
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["episodes"] = Episode.objects.filter().order_by("-pub_date")[:10]
        return context
    
class SearchResultsListView(ListView):
    template_name = "search_results.html"
    model = Episode
    context_object_name = "episode_list"

    def get_queryset(self):
        query = self.request.GET.get("q")
        return Episode.objects.filter(
            Q(title__icontains=query) | Q(podcast_name__icontains=query)
        )