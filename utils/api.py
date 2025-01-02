from datetime import date
from aiohttp import ClientSession
from utils.models import Seminar


class ApiWrapper:
    def __init__(self):
        self.session = None

    async def setup(self, session: ClientSession):
        self.session = session

    async def fetch_seminars(self, start_date: date, end_date: date):
        url = f'api/seminars/?start_date={start_date or ''}&end_date={end_date or ''}&limit=100&display_only=1'
        async with self.session.get(url) as resp:
            data = await resp.json()
            if not data['count']:
                return []

            results = data['results']
            while data['next']:
                resp = await self.session.get(data['next'])
                data = await resp.json()
                results += data['results']

            return [Seminar.from_json(result) for result in results]

    async def fetch_seminar(self, seminar_id: int):
        url = f'api/seminars/{seminar_id}/?display_only=1'
        async with self.session.get(url) as resp:
            data = await resp.json()
            return Seminar.from_json(data)

    async def fetch_template(self, template_id: int):
        url = f'api/GoogleFormTemplate/{template_id}/'
        async with self.session.get(url) as resp:
            data = await resp.json()
            file_url = data['file']
            print(file_url)
            file_url = file_url[file_url.find('media'):]
        print(file_url)
        async with self.session.get(file_url) as resp:
            print(resp.status)
            template = await resp.json()
            print(template)
            return template

    async def post_seminar(self, seminar: Seminar):
        url = f'api/seminars/{seminar.id}/'
        seminar_data = seminar.to_json()
        async with self.session.post(url, json=seminar_data) as resp:
            if resp.status == 201:
                return await resp.json()
            else:
                raise Exception(f"Failed to post seminar. Status code: {resp.status}")

    async def fetch_next_reminder(self):
        url = f'api/reminders/?only_next=1'
        async with self.session.get(url) as resp:
            return (await resp.json())['results']

    async def mark_reminder_as_pinged(self,reminder_id: int):
        url = f'api/reminders/{reminder_id}/'
        data = {"pinged": True}
        try:
            async with self.session.patch(url, json=data) as response:
                if response.status == 200:
                    # Successfully updated the reminder
                    print(f"Reminder {reminder_id} marked as pinged.")
                    return await response.json()  # Optionally return the response data
                else:
                    print(f"Failed to update reminder {reminder_id}. Status code: {response.status}")
                    return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
