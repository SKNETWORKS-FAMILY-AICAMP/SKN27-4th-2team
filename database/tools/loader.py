from langchain_community.document_loaders import JSONLoader

def dog_info_metadata_func(record: dict, metadata: dict) -> dict:
    metadata['source'] = 'American Kennel Club'
    metadata['doc_id'] = record.get('doc_id')
    metadata['doc_type'] = record.get('doc_type')
    metadata['section'] = record.get('section')
    return metadata

def get_dog_info_loader(filepath='../contents/dog_info/preprocessed/akc_breed_info_vector_documents.json'):
    loader = JSONLoader(
        filepath=filepath,
        jq_schema = r'.[]', 
        content_key='content', 
        metadata_func=dog_info_metadata_func,
        text_content=False
    )
    return loader

def article_metadata_func(record: dict, metadata: dict) -> dict:
    metadata['doc_id'] = record.get('id')
    metadata['doc_type'] = record.get('metadata').get('doc_type')
    metadata['category'] = record.get('metadata').get('category')
    metadata['title'] = record.get('metadata').get('title')
    metadata['updated_date'] = record.get('metadata').get('updated_date')
    metadata['author'] = record.get('metadata').get('author')
    metadata['tags'] = record.get('metadata').get('tags')
    metadata['section_title'] = record.get('metadata').get('section_title')
    metadata['source'] = 'American Kennel Club'
    metadata['url'] = record.get('metadata').get('url')
    return metadata

def get_article_loader(filepath):
    """
    filepath example: '../../docs/article_dog-breeds.json'
    """
    loader = JSONLoader(
        filepath=filepath,
        jq_schema = r'.[]', 
        content_key='content', 
        metadata_func=article_metadata_func,
        text_content=False
    )
    return loader

