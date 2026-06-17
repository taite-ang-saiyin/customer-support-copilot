# Customer-Facing Help Articles

These Markdown files are sample public help articles derived from the existing synthetic CloudDesk knowledge base.

They are intended for testing the help-article API and customer portal flows. Each article includes front matter with:

- `title`
- `category`
- `access_level: public`
- `source_type: help_article`
- `summary`

Example upload:

```bash
curl -X POST http://localhost:8000/knowledge/upload \
  -H "X-API-Key: change-me-dev-key" \
  -F "file=@sample_knowledge/help_articles/refund_requests.md" \
  -F "title=Refund Requests" \
  -F "source_type=help_article" \
  -F "category=Billing" \
  -F "access_level=public"
```
