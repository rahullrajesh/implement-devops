# Dataset: image_classification_dataset
# Table name: image_text_detail
import os
import sys

# Import Google Cloud Library modules
from google.cloud import storage, bigquery, language, vision
client = vision.ImageAnnotatorClient()

if ('GOOGLE_APPLICATION_CREDENTIALS' in os.environ):
    if (not os.path.exists(os.environ['GOOGLE_APPLICATION_CREDENTIALS'])):
        print ("The GOOGLE_APPLICATION_CREDENTIALS file does not exist.\n")
        exit()
else:
    print ("The GOOGLE_APPLICATION_CREDENTIALS environment variable is not defined.\n")
    exit()

if len(sys.argv)<3:
    print('You must provide parameters for the Google Cloud project ID and Storage bucket')
    print ('python3 '+sys.argv[0]+ '[PROJECT_NAME] [BUCKET_NAME]')
    exit()

project_name = sys.argv[1]
bucket_name = sys.argv[2]

# Set up our GCS, BigQuery, and Natural Language clients
storage_client = storage.Client()
bq_client = bigquery.Client(project=project_name)
nl_client = language.LanguageServiceClient()

# Set up client objects for the vision and translate_v2 API Libraries
vision_client = vision.ImageAnnotatorClient()

# Setup the BigQuery dataset and table objects
dataset_ref = bq_client.dataset('image_classification_dataset')
dataset = bigquery.Dataset(dataset_ref)
table_ref = dataset.table('image_text_detail')
table = bq_client.get_table(table_ref)

# Create an array to store results data to be inserted into the BigQuery table
rows_for_bq = []

# Get a list of the files in the Cloud Storage Bucket
files = storage_client.bucket(bucket_name).list_blobs()
bucket = storage_client.bucket(bucket_name)

print('Processing image files from GCS. This will take a few minutes..')

# Process files from Cloud Storage and save the result to send to BigQuery
for file in files:    
    if file.name.endswith('jpg') or  file.name.endswith('png'):
        file_content = file.download_as_string()
        
        # TBD: Create a Vision API image object called image_object
        image_object = vision.Image(content=file_content)
        # Ref: https://googleapis.dev/python/vision/latest/gapic/v1/types.html#google.cloud.vision_v1.types.Image


        # TBD: Detect text in the image and save the response data into an object called response
        response = client.text_detection(image=image_object)
        # Ref: https://googleapis.dev/python/vision/latest/gapic/v1/api.html#google.cloud.vision_v1.ImageAnnotatorClient.document_text_detection

    
        # Save the text content found by the vision API into a variable called text_data
        text_data = response.text_annotations[0].description

        # Save the text detection response data in <filename>.txt to cloud storage
        file_name = file.name.split('.')[0] + '.txt'
        blob = bucket.blob(file_name)
        # Upload the contents of the text_data string variable to the Cloud Storage file 
        blob.upload_from_string(text_data, content_type='text/plain')

        # Extract the description and locale data from the response file
        # into variables called desc and locale
        # using response object properties e.g. response.text_annotations[0].description
        desc = response.text_annotations[0].description
        locale = response.text_annotations[0].locale
        
        # if the locale is English (en) save the description as the translated_txt
        if locale == 'en':
            translated_text = desc
        else:
            # TBD: For non EN locales pass the description data to the translation API
            # ref: https://googleapis.dev/python/translation/latest/client.html#google.cloud.translate_v2.client.Client.translate
            # Set the target_language locale to 'en')
            from google.cloud import translate_v2 as translate
            translate_client = translate.Client()
            translation = translate_client.translate(desc, target_language='en',format_='text')
            translated_text = translation['translatedText']
        print(translated_text)
        
        # if there is response data save the original text read from the image, 
        # the locale, translated text, and filename
        if len(response.text_annotations) > 0:
            rows_for_bq.append((desc, locale, translated_text, file.name))

print('Writing Vision API image data to BigQuery...')
# Write original text, locale and translated text to BQ
# TBD: When the script is working uncomment the next line to upload results to BigQuery
errors = bq_client.insert_rows(table, rows_for_bq)
assert errors == []
