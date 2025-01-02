from apiclient import discovery
from httplib2 import Http
from oauth2client import client, file, tools

SCOPES = "https://www.googleapis.com/auth/forms.body"
DISCOVERY_DOC = "https://forms.googleapis.com/$discovery/rest?version=v1"

store = file.Storage("token.json")
creds = store.get()
if not creds or creds.invalid:
  flow = client.flow_from_clientsecrets("client_secret.json", SCOPES)
  creds = tools.run_flow(store)

form_service = discovery.build(
    "forms",
    "v1",
    http=creds.authorize(Http()),
    discoveryServiceUrl=DISCOVERY_DOC,
    static_discovery=False,
)

async def create_from_template(template,title: str):
    """
    Creates and post Google form from template (loaded json).
    Returns:
    link to Form (for edit) and for view.
    """
    NEW_FORM = {
        "info": {
            "title": title,
        }
    }
    try:
        # Create the Google Form using the template
        result = form_service.forms().create(body=NEW_FORM).execute()
        batch_update_body = {"requests": []}
        form_id = result.get("formId")
        form_url_edit = f"https://docs.google.com/forms/d/{form_id}/edit"
        form_url_viewset = f"https://docs.google.com/forms/d/{form_id}/viewform"
        if "description" in template["info"]:
            batch_update_body["requests"].append({
                "updateFormInfo": {
                    "info": {"description": template["info"]["description"]},
                    "updateMask": "description"
                }
            })
        if "items" in template:
            for index, item in enumerate(template["items"]):
                batch_update_body["requests"].append({
                    "createItem": {
                        "item": item,
                        "location": {"index": index},
                    }
                })
        if batch_update_body["requests"]:
            form_service.forms().batchUpdate(formId=form_id, body=batch_update_body).execute()
            print("Form updated successfully with description and items.")

        print(f"Form created successfully: {form_url_edit}")
        return form_url_viewset,form_url_edit
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
