
import asyncio
from sqlalchemy import select
from app.database.engine import engine
from app.database.session import async_session_factory
from app.models.document import Document

async def test():
    async with async_session_factory() as session:
        file_hash = '5d16d064a1c354991a95f74e44dc7de220742352af56844d309411440e504e8b'
        stmt = select(Document).where(Document.metadata_['file_hash'].astext == file_hash)
        result = await session.execute(stmt)
        docs = result.scalars().all()
        print('Docs found:', len(docs))
        for d in docs:
            print('ID:', d.id, 'Hash:', d.metadata_.get('file_hash'))

asyncio.run(test())

