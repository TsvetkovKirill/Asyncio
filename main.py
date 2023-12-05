
import asyncio
from models import SwapiPeople, Base, Session, engine
from more_itertools import chunked
from aiohttp import ClientSession
import datetime


CHUNK_SIZE = 2
BASE_URL = 'https://swapi.dev/api/people/'


async def chunked_async(async_iter, size):

    buffer = []
    while True:
        try:
            item = await async_iter.__anext__()
        except StopAsyncIteration:
            if buffer:
                yield buffer
            break
        buffer.append(item)
        if len(buffer) == size:
            yield buffer
            buffer = []


async def get_fields(url_list, session: ClientSession, field="name"):
    fields = []
    for url in url_list:
        async with session.get(url) as response:
            data = await response.json()
            fields.append(data[field])
    return ', '.join(fields)


async def get_person(person_id: int, session: ClientSession):
    async with session.get(f'{BASE_URL}{person_id}/') as response:
        if response.status == 404:
            return
        json_data = await response.json()
        person = {
            "id": person_id,
            "birth_year": json_data["birth_year"],
            "eye_color": json_data["eye_color"],
            "films": await get_fields(json_data["films"], session, field="title"),
            "gender": json_data["gender"],
            "hair_color": json_data["hair_color"],
            "height": json_data["height"],
            "homeworld": await get_fields([json_data["homeworld"]], session),
            "mass": json_data["mass"],
            "name": json_data["name"],
            "skin_color": json_data["skin_color"],
            "species": await get_fields(json_data["species"], session),
            "starships": await get_fields(json_data["starships"], session),
            "vehicles": await get_fields(json_data["vehicles"], session),
        }
        print(person)
        return person


async def get_people(person_ids: list):
    async with ClientSession() as session:
        for chunk in chunked(person_ids, CHUNK_SIZE):
            person_list = [get_person(person_id, session=session) for person_id in chunk]
            persons_chunk = await asyncio.gather(*person_list)
            for item in persons_chunk:
                yield item


async def insert_people(people_chunk):
    async with Session() as session:
        session.add_all([SwapiPeople(**item) for item in people_chunk if item is not None])
        await session.commit()


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        await conn.commit()

    async for item in chunked_async(get_people(range(1, 4)), CHUNK_SIZE):
        asyncio.create_task(insert_people(item))

    tasks_in_work = set(asyncio.all_tasks()) - {asyncio.current_task()}
    for task in tasks_in_work:
        await task


start = datetime.datetime.now()
asyncio.run(main())
print(datetime.datetime.now() - start)