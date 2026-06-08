from pathlib import Path

from langchain_community.document_loaders import JSONLoader


QNA_SOURCE_METADATA = {
    "final_seol_qna": {
        "expert": "설채현 수의사",
        "expert_role": "veterinarian",
        "channel": "설채현의 놀로와",
        "content_category": "veterinary_knowledge",
    },
    "kang_qna": {
        "expert": "강형욱 훈련사",
        "expert_role": "trainer",
        "channel": "강형욱의 보듬TV",
        "content_category": "behavior_training",
    },
}


def dog_info_metadata_func(record: dict, metadata: dict) -> dict:
    metadata["source"] = "American Kennel Club"
    metadata["doc_id"] = record.get("doc_id")
    metadata["doc_type"] = record.get("doc_type")
    metadata["section"] = record.get("section")
    return metadata


def get_dog_info_loader(
    filepath="../akc/preprocessed/akc_breed_info_vector_documents.json",
):
    return JSONLoader(
        file_path=filepath,
        jq_schema=r".[]",
        content_key="content",
        metadata_func=dog_info_metadata_func,
        text_content=False,
    )


def article_metadata_func(record: dict, metadata: dict) -> dict:
    record_metadata = record.get("metadata") or {}

    metadata["doc_id"] = record.get("id")
    metadata["doc_type"] = record_metadata.get("doc_type")
    metadata["category"] = record_metadata.get("category")
    metadata["title"] = record_metadata.get("title")
    metadata["updated_date"] = record_metadata.get("updated_date")
    metadata["author"] = record_metadata.get("author")
    metadata["tags"] = record_metadata.get("tags")
    metadata["section_title"] = record_metadata.get("section_title")
    metadata["source"] = "American Kennel Club"
    metadata["url"] = record_metadata.get("url")
    return metadata


def get_article_loader(filepath):
    """
    filepath example: '../../docs/article_dog-breeds.json'
    """
    return JSONLoader(
        file_path=filepath,
        jq_schema=r".[]",
        content_key="content",
        metadata_func=article_metadata_func,
        text_content=False,
    )


def youtube_metadata_func(record: dict, metadata: dict) -> dict:
    record_metadata = record.get("metadata") or {}

    metadata["doc_id"] = record.get("id")
    metadata["doc_type"] = record_metadata.get("doc_type")
    metadata["channel"] = record_metadata.get("channel")
    metadata["title"] = record_metadata.get("title")
    metadata["url"] = record_metadata.get("video_url")
    metadata["expert"] = record_metadata.get("expert")
    metadata["source"] = "YouTube"
    return metadata


def get_youtube_loader(filepath):
    """
    filepath example: '../../docs/youtube_basic_instruction.json'
    """
    return JSONLoader(
        file_path=filepath,
        jq_schema=r".[]",
        content_key="content",
        metadata_func=youtube_metadata_func,
        text_content=False,
    )

def merck_metadata_func(record: dict, metadata: dict) -> dict:
    metadata["source"] = record.get("source") or "merck_vet_manual"
    metadata["doc_type"] = "medical_reference"
    metadata["scope"] = record.get("scope")
    metadata["title"] = record.get("title")
    metadata["url"] = record.get("url")
    metadata["category"] = record.get("category")
    metadata["section_slug"] = record.get("section_slug")
    metadata["reviewed_date"] = record.get("reviewed_date")
    metadata["author"] = record.get("author")
    metadata["language"] = record.get("language") or "en"
    metadata["crawled_at"] = record.get("crawled_at")
    metadata["medical_disclaimer_required"] = True
    return metadata


def get_merck_loader(filepath):
    """
    filepath example: '../../merck_vet/raw/routine-health-care-of-dogs.json'
    """
    return JSONLoader(
        file_path=filepath,
        jq_schema=r".",
        content_key="content",
        metadata_func=merck_metadata_func,
        text_content=False,
    )
def qna_metadata_func(qna_source: str, source_file: str):
    source_metadata = QNA_SOURCE_METADATA.get(qna_source, {})

    def _metadata_func(record: dict, metadata: dict) -> dict:
        metadata["source"] = "qna"
        metadata["doc_type"] = "qna"
        metadata["qna_source"] = qna_source
        metadata["source_file"] = source_file
        metadata["language"] = "ko"
        metadata["source_origin"] = "youtube_processed_qna"
        metadata["expert"] = source_metadata.get("expert")
        metadata["expert_role"] = source_metadata.get("expert_role")
        metadata["channel"] = source_metadata.get("channel")
        metadata["content_category"] = source_metadata.get("content_category")
        return metadata

    return _metadata_func


def get_qna_loader(filepath, qna_source):
    return JSONLoader(
        file_path=filepath,
        jq_schema=r'''
        {
          content: (
            "Question:\n"
            + (.question // .Question // .["질문"] // "")
            + "\n\nAnswer:\n"
            + (.answer // .Answer // .["답변"] // "")
          )
        }
        ''',
        content_key="content",
        metadata_func=qna_metadata_func(
            qna_source=qna_source,
            source_file=Path(filepath).name,
        ),
        text_content=False,
        json_lines=True,
    )

