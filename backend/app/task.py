import asyncio
from typing import Any, Dict

from celery import current_task

from app.core.database import AsyncSessionLocal
from app.services.document_processor import document_processor
from app.worker import celery_app


@celery_app.task(bind=True)
def process_document_task(
    self: Any, document_id: int, file_path: str
) -> Dict[str, Any]:
    """Celery task for document processing."""

    async def async_process() -> Dict[str, Any]:
        async with AsyncSessionLocal() as db:
            try:
                # Update task status
                current_task.update_state(
                    state="PROCESSING",
                    meta={"status": "Starting document processing"},
                )

                # Process document
                result = await document_processor.process_document(
                    db, document_id, file_path
                )

                return result

            except Exception as e:
                current_task.update_state(
                    state="FAILURE", meta={"error": str(e)}
                )
                raise

    # Run async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(async_process())
