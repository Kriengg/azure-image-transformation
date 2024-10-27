import os
import azure.functions as func
import logging
from azure.storage.blob import BlobServiceClient
from PIL import Image
import io

# Initialize BlobServiceClient and container clients
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
if not connection_string:
    raise ValueError("AZURE_STORAGE_CONNECTION_STRING environment variable is not set")

blob_service_client = BlobServiceClient.from_connection_string(connection_string)
assets_container_client = blob_service_client.get_container_client("assets")
output_container_client = blob_service_client.get_container_client("assetsoutput")

# Ensure the output container exists
try:
    output_container_client.create_container()
except Exception as e:
    logging.info(f"Container 'assetsoutput' already exists or could not be created: {e}")

# Mapping of file extensions to MIME types
MIME_TYPES = {
    "JPEG": "image/jpeg",
    "JPG": "image/jpeg",
    "PNG": "image/png",
    "BMP": "image/bmp",
    "GIF": "image/gif"
}

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="dynamicmediahandler")
def dynamicmediahandler(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    filename = req.params.get('filename')
    width = req.params.get('width')
    height = req.params.get('height')
    format = req.params.get('format')

    if not filename:
        return func.HttpResponse(
            "Filename is required.",
            status_code=400
        )

    # Check if the filename has an extension
    if '.' not in filename:
        logging.info(f"Filename does not have an extension. Using default image.")
        filename = "no-image.jpg"

    # Determine the MIME type based on the file extension
    original_extension = filename.split('.')[-1].upper()
    mimetype = MIME_TYPES.get(original_extension, "application/octet-stream")

    # Generate the output filename
    output_filename = f"{filename.split('.')[0]}_{width}_{height}.{format.lower() if format else original_extension.lower()}"

    # Check if the transformed image already exists in the output container
    output_blob_client = output_container_client.get_blob_client(blob=output_filename)
    try:
        output_blob_data = output_blob_client.download_blob().readall()
        logging.info(f"Transformed image already exists: {output_filename}")
        return func.HttpResponse(
            output_blob_data,
            mimetype=MIME_TYPES.get(format.upper() if format else original_extension, "application/octet-stream"),
            headers={
                "Content-Disposition": f"inline; filename={output_filename}"
            }
        )
    except Exception:
        logging.info(f"Transformed image does not exist: {output_filename}. Proceeding with transformation.")

    # Attempt to download the original image from the assets container
    blob_client = assets_container_client.get_blob_client(blob=filename)
    try:
        logging.info(f"Attempting to download blob: {filename} from container: assets")
        blob_data = blob_client.download_blob().readall()
        logging.info(f"Successfully downloaded blob: {filename}")
    except Exception as e:
        logging.error(f"Error downloading blob: {e}. Using default image.")
        # Use default image if the specified image is not found
        default_filename = "no-image.jpg"
        blob_client = assets_container_client.get_blob_client(blob=default_filename)
        try:
            blob_data = blob_client.download_blob().readall()
            logging.info(f"Successfully downloaded default image: {default_filename}")
            # Update filename to default filename for further processing
            filename = default_filename
        except Exception as e:
            logging.error(f"Error downloading default image: {e}")
            return func.HttpResponse(
                "Error downloading the image.",
                status_code=500
            )

    # If width, height, and format are not provided, return the existing image
    if not width and not height and not format:
        return func.HttpResponse(
            blob_data,
            mimetype=mimetype
        )

    # Transform the image based on the input criteria
    try:
        image = Image.open(io.BytesIO(blob_data))
        logging.info(f"Original image size: {image.size}")
        original_width, original_height = image.size

        # Resize the image according to parameters, avoiding upscaling
        if width and height:
            width = int(width)
            height = int(height)
            image.thumbnail((width, height))
        elif width:
            width = int(width)
            height = int(original_height * (width / original_width))
            image.thumbnail((width, height))
        elif height:
            height = int(height)
            width = int(original_width * (height / original_height))
            image.thumbnail((width, height))
        logging.info(f"Transformed image size: {image.size}")

        # Determine the format for saving
        if format:
            format = format.upper()
            if format == "JPG":
                format = "JPEG"
            if format not in ["JPEG", "PNG", "BMP", "GIF"]:
                return func.HttpResponse(
                    "Unsupported format.",
                    status_code=400
                )
        else:
            # Use the format of the original file extension
            if original_extension == "JPG":
                format = "JPEG"
            elif original_extension in ["JPEG", "PNG", "BMP", "GIF"]:
                format = original_extension
            else:
                return func.HttpResponse(
                    "Unsupported format.",
                    status_code=400
                )

        output = io.BytesIO()
        image.save(output, format=format)
        output.seek(0)

        # Upload the transformed image to the output container
        output_blob_client.upload_blob(output, overwrite=True)

        # Return the transformed image with the correct filename
        output.seek(0)
        return func.HttpResponse(
            output.read(),
            mimetype=MIME_TYPES.get(format, "application/octet-stream"),
            headers={
                "Content-Disposition": f"inline; filename={output_filename}"
            }
        )

    except Exception as e:
        logging.error(f"Error processing image: {e}")
        return func.HttpResponse(
            "Error processing the image.",
            status_code=500
        )