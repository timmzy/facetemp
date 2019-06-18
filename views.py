# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.views.generic.detail import DetailView
from django.views.generic import View
from django.views.generic.list import ListView
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.template import RequestContext
from django.core.management import call_command
from django.core.urlresolvers import reverse
from django.conf import settings
from django.http import HttpResponseForbidden
from django.contrib.sites.shortcuts import get_current_site

import requests, logging

from allauth.socialaccount.models import SocialAccount

from .models import App, Record, Story, AdSnippet, Lang
from .utils import process_app, get_or_none

logger = logging.getLogger('funapps')


class AdSnippetConfig(object):
    ad_above_content = 'ad_above_content'
    ad_below_image = 'ad_below_image'
    ad_below_content = 'ad_below_content'
    ad_sidebar_content = 'ad_sidebar_content'
    ad_header = 'header_scripts'
    ad_footer = 'footer_scripts'


class AdsMixin(object):

    def get_context_data(self, **kwargs):
        context = super(AdsMixin, self).get_context_data(**kwargs)
        current_site = get_current_site(request=None)
        ad_snippet = get_or_none(AdSnippet, site=current_site)
        apps = App.objects.filter(paused=False).exclude(pk=kwargs.get('object').pk).order_by('?')[:12]
        context['languages'] = Lang.objects.values('name', 'code')
        if ad_snippet:
            context[AdSnippetConfig.ad_above_content] = ad_snippet.ad_above_content
            context[AdSnippetConfig.ad_below_image] = ad_snippet.ad_below_image
            context[AdSnippetConfig.ad_below_content] = ad_snippet.ad_below_content
            context[AdSnippetConfig.ad_sidebar_content] = ad_snippet.ad_sidebar_content
            context[AdSnippetConfig.ad_header] = ad_snippet.header
            context[AdSnippetConfig.ad_footer] = ad_snippet.footer
        return context


class AppDetailView(AdsMixin, DetailView):
    model = App
    template_name = 'content/detail.html'

    def get_context_data(self, **kwargs):
        context = super(AppDetailView, self).get_context_data(**kwargs)
        context['is_detail_view'] = True;
        context['is_google'] = True if self.request.GET.get('utm_source') == 'google' else False
        context['scope'] = ','.join(kwargs.get('object').permissions)
        if self.request.user.is_authenticated() and not self.request.user.is_superuser:
            context['uid'] = getattr(self.request.user.socialaccount_set.first(), 'uid', 4)
        apps = self.model.objects.filter(paused=False).exclude(pk=kwargs.get('object').pk).order_by('?')[:12]
        context['slug'] = self.model.objects.get(pk=kwargs.get('object').pk)
        print(self.kwargs['slug'])
        context['apps'] = apps
        return context


class StoryDetailView(AdsMixin, DetailView):
    model = Story
    template_name = 'content/story_detail.html'

    def get_context_data(self, **kwargs):
        context = super(StoryDetailView, self).get_context_data(**kwargs)
        context['is_detail_view'] = True;
        if self.request.user.is_authenticated() and not self.request.user.is_superuser:
            context['uid'] = getattr(self.request.user.socialaccount_set.first(), 'uid', 4)
        apps = self.model.objects.filter(paused=False).exclude(pk=kwargs.get('object').pk).order_by('?')[:12]
        context['apps'] = apps
        return context


class AccountView(TemplateView):
    template_name = 'content/profile.html'


class IndexView(ListView):
    template_name = 'content/index.html'
    paginate_by = 13
    model = App

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        context['is_detail_view'] = False;
        context['languages'] = Lang.objects.values('name', 'code')
        if self.request.user.is_authenticated() and not self.request.user.is_superuser:
            context['uid'] = getattr(self.request.user.socialaccount_set.first(), 'uid', 4)
        return context

    def get_queryset(self):
        if settings.LOCALE_ENABLED:
            try:
                code = self.request.META['HTTP_HOST'].split('.')[0]
            except Exception as e:
                code = u'en'
            try:
                lang_code = Lang.objects.get(code=code)
            except Exception as e:
                lang_code = Lang.objects.get(code=u'en')
            qs = self.model.objects.filter(paused=False, languages__in=[lang_code]).order_by('-created')
        else:
            qs = self.model.objects.filter(paused=False).order_by('-created')
        qs = qs.prefetch_related('tags')
        return qs


class AppResultView(AdsMixin, DetailView):
    template_name = 'content/result.html'
    model = App

    def get_context_data(self, **kwargs):
        uid = self.kwargs.get('uid')
        context = super(AppResultView, self).get_context_data(**kwargs)
        if self.request.user.is_authenticated() and not self.request.user.is_superuser:
            context['uid'] = getattr(self.request.user.socialaccount_set.first(), 'uid', 4)
        apps = self.model.objects.filter(paused=False).exclude(pk=kwargs.get('object').pk).order_by('?')[:12]
        context['apps'] = apps
        context['random_app'] = apps[0]
        context['is_detail_view'] = False
        try:
            user = SocialAccount.objects.filter(uid=self.kwargs.get('uid')).first().user
            record = Record.objects.filter(app=kwargs.get('object'), user=user).first()
            if record and record.image:
                context['result_image'] = record.image
            else:
                context['result_image'] = kwargs.get('object').og_image
        except AttributeError as e:
            logging.info('AttributeError at {}'.format(e))
            context['result_image'] = kwargs.get('object').og_image
        except Exception as e:
            logging.info('AttributeError at {}'.format(e))
            context['result_image'] = kwargs.get('object').og_image
        return context


class ResultView(AdsMixin, DetailView):
    template_name = 'content/result_ajax.html'
    model = App

    def get_context_data(self, **kwargs):
        uid = self.kwargs.get('uid')
        context = super(ResultView, self).get_context_data(**kwargs)
        context['is_detail_view'] = False
        if self.request.user.is_authenticated() and not self.request.user.is_superuser:
            context['uid'] = getattr(self.request.user.socialaccount_set.first(), 'uid', 4)
        apps = self.model.objects.filter(paused=False).exclude(pk=kwargs.get('object').pk).order_by('?')[:12]
        # Remove later
        apps = self.model.objects.all()
        context['apps'] = apps
        context['random_app'] = apps[0]
        return context

    def get(self, request, *args, **kwargs):
        print(self.request.GET)
        """
        if not self.request.user.is_authenticated():
            return HttpResponseRedirect(reverse('mysite:detail_app', kwargs=kwargs))
        """
        return super(ResultView, self).get(request, *args, **kwargs)


def bad_request(request):
    return redirect(reverse('mysite:index'))


def page_not_found(request):
    return redirect(reverse('mysite:index'))


def server_error(request):
    return redirect(reverse('mysite:index'))


class RecordMonitorView(ListView):
    model = Record
    paginate_by = 60
    template_name = 'content/record_monitoring.html'
    context_object_name = 'records'

    def get_queryset(self):
        queryset = super(RecordMonitorView, self).get_queryset()
        queryset = queryset.order_by('-id')
        return queryset

    def get(self, request, *args, **kwargs):
        if not self.request.user.is_superuser:
            return HttpResponseForbidden()
        return super(RecordMonitorView, self).get(request, *args, **kwargs)


class PhotoView(AdsMixin, DetailView):
    model = App
    template_name = 'content/photos.html'

    def get_context_data(self, **kwargs):
        uid = self.kwargs.get('uid')
        context = super(PhotoView, self).get_context_data(**kwargs)
        context['is_detail_view'] = False;
        if self.request.user.is_authenticated() and not self.request.user.is_superuser:
            context['uid'] = getattr(self.request.user.socialaccount_set.first(), 'uid', 4)
        apps = self.model.objects.filter(paused=False).exclude(pk=kwargs.get('object').pk).order_by('?')[:12]
        context['apps'] = apps
        return context
