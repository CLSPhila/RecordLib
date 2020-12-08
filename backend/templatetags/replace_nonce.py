from django import template
from webpack_loader.templatetags.webpack_loader import render_bundle

register = template.Library()


@register.simple_tag()
def replace_nonce(bundle, nonce="", *args, **kwargs):
    return render_bundle(bundle, attrs=f"nonce='nonce-{nonce}'")

