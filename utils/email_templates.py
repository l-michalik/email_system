from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmailTemplateContent:
    subject: str
    title: str
    subtitle: str
    body_text: str
    button_label: str
    button_link: str


def build_email_text(content: EmailTemplateContent) -> str:
    return (
        f"{content.title}\n\n"
        f"{content.subtitle}\n\n"
        f"{content.body_text}\n\n"
        f"{content.button_label}: {content.button_link}\n"
    )


def build_email_html(content: EmailTemplateContent) -> str:
    subtitle = content.subtitle.replace("\n", "<br>")
    body_text = content.body_text.replace("\n", "<br>")

    return f"""
<div style="margin:0!important;padding:0!important;background-color:#f5f1ea">
  <div role="article" aria-label="Joule email" lang="en" style="background-color:#ffffff;color:#1f2933;font-family:'Open Sans',HelveticaNeue,Arial,Helvetica,sans-serif;font-size:18px;font-weight:400;line-height:28px;margin:0 auto;max-width:600px;padding:40px 24px">
    <header>
      <center>
        <img src="https://joule.weareamnet.com/amnet/public/siteelements/placeholder.png" alt="" width="80" style="height:auto">
      </center>
      <h1 style="color:#111111;font-size:32px;font-weight:800;line-height:40px;margin:40px 0 12px;text-align:center">
        {content.title}
      </h1>
      <p style="color:#6b7280;font-size:18px;font-weight:600;line-height:28px;margin:0;text-align:center">
        {subtitle}
      </p>
    </header>
    <img src="https://joule.weareamnet.com/amnet/public/siteelements/Joule_inline_colur_filled.png" alt="" width="600" border="0" style="border-radius:4px;display:block;margin:32px 0;max-width:100%;min-width:100px;width:100%">
    <p style="margin:0 0 32px">
      {body_text}
    </p>
    <center>
      <div style="margin:40px 0 0">
        <a href="{content.button_link}" target="_blank" style="background-color:#ee5a24;border-radius:4px;color:#ffffff;display:inline-block;font-family:'Open Sans',HelveticaNeue,Arial,Helvetica,sans-serif;font-size:18px;font-weight:bold;line-height:60px;text-align:center;text-decoration:none;width:300px">
          {content.button_label}
        </a>
      </div>
    </center>
  </div>
</div>
""".strip()
