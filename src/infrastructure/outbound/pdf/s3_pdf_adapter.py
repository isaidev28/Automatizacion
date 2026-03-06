import boto3
import pdfplumber
import io
from src.domain.ports.outbound.i_pdf_service import IPDFService
from src.domain.entities.pdf_contenido import PdfContenido
from src.domain.exceptions.clase_exception import PDFInvalidoException
from urllib.parse import unquote

class S3PDFAdapter(IPDFService):

    def __init__(
        self,
        aws_access_key: str,
        aws_secret_key: str,
        region: str,
        bucket_name: str
    ):
        self._s3 = boto3.client(
            "s3",
            aws_access_key_id     = aws_access_key,
            aws_secret_access_key = aws_secret_key,
            region_name           = region
        )
        self._bucket = bucket_name

    def _extraer_key_de_url(self, url: str) -> str:
        if not url:
            raise PDFInvalidoException("URL del PDF no puede ser None o vacía")

        if "amazonaws.com" in url:
            partes = url.split("amazonaws.com/")
            key = partes[-1]
            if key.startswith(self._bucket + "/"):
                key = key[len(self._bucket) + 1:]
            return unquote(key)     # ← esta es la línea que cambia

        raise PDFInvalidoException(f"URL de S3 no válida: {url}")

    async def extraer_contenido(self, url_s3: str) -> PdfContenido:
        try:
            # 1. Extraer key del objeto desde la URL
            key = self._extraer_key_de_url(url_s3)

            # 2. Descargar PDF desde S3 a memoria
            response = self._s3.get_object(
                Bucket = self._bucket,
                Key    = key
            )
            pdf_bytes = response["Body"].read()

            # 3. Parsear PDF con pdfplumber
            texto_completo = ""
            temas          = []
            total_paginas  = 0

            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                total_paginas = len(pdf.pages)

                for i, pagina in enumerate(pdf.pages):
                    texto_pagina = pagina.extract_text()
                    if texto_pagina:
                        texto_completo += f"\n--- Página {i + 1} ---\n"
                        texto_completo += texto_pagina

                        # Extraer primera línea de cada página como tema
                        lineas = texto_pagina.strip().split("\n")
                        if lineas and len(lineas[0]) > 5:
                            temas.append(lineas[0][:100])

            if not texto_completo.strip():
                raise PDFInvalidoException("El PDF no contiene texto extraíble")

            return PdfContenido(
                url_origen     = url_s3,
                texto_completo = texto_completo.strip(),
                temas          = temas[:20],        # Máximo 20 temas
                total_paginas  = total_paginas,
            )

        except PDFInvalidoException:
            raise
        except Exception as e:
            raise PDFInvalidoException(f"Error procesando PDF desde S3: {str(e)}")