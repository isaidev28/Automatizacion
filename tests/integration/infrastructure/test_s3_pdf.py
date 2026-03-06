import pytest
import os
from dotenv import load_dotenv
from src.infrastructure.outbound.pdf.s3_pdf_adapter import S3PDFAdapter

load_dotenv()

TEST_URL = "https://mentorpdf.s3.amazonaws.com/pdfs/Diagramas%20historias%20de%20usuario.pdf"


@pytest.fixture
def adapter():
    return S3PDFAdapter(
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY"),
        region         = os.getenv("AWS_REGION"),
        bucket_name    = os.getenv("AWS_BUCKET_NAME")
    )


@pytest.mark.asyncio
async def test_extraer_pdf_desde_s3(adapter):
    contenido = await adapter.extraer_contenido(TEST_URL)

    print(f"\n PDF extraído correctamente")
    print(f"   Páginas:  {contenido.total_paginas}")
    print(f"   Temas:    {contenido.temas[:3]}")
    print(f"   Texto:    {contenido.texto_completo[:200]}...")

    assert contenido.texto_completo is not None
    assert len(contenido.texto_completo) > 50
    assert contenido.total_paginas > 0


def test_extraer_key_de_url(adapter):
    casos = [
        (
            "https://mentorpdf.s3.amazonaws.com/pdfs/clase.pdf",
            "pdfs/clase.pdf"
        ),
        (
            "https://s3.us-east-1.amazonaws.com/mentorpdf/pdfs/clase.pdf",
            "pdfs/clase.pdf"
        ),
    ]
    for url, key_esperado in casos:
        key = adapter._extraer_key_de_url(url)
        print(f"\n🔑 Key obtenido: {key}")
        assert key == key_esperado