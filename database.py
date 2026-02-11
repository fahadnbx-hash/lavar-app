def upload_to_drive(file_content, file_name):
    try:
        creds = get_creds()
        from googleapiclient.discovery import build
        service = build('drive', 'v3', credentials=creds)
        
        file_metadata = {
            'name': file_name, 
            'mimeType': 'application/pdf',
            'parents': [FOLDER_ID]
        }
        
        media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='application/pdf', resumable=True)
        
        # التعديل هنا: إضافة supportsAllDrives لضمان استخدام مساحة المجلد المشترك
        file = service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id, webViewLink',
            supportsAllDrives=True 
        ).execute()
        
        # جعل الملف متاحاً للقراءة
        service.permissions().create(
            fileId=file.get('id'), 
            body={'type': 'anyone', 'role': 'reader'},
            supportsAllDrives=True
        ).execute()
        
        return file.get('webViewLink')
    except Exception as e:
        st.error(f"خطأ في الرفع: {str(e)}")
        # إذا استمر الخطأ، سنعرض رسالة توضيحية للمستخدم
        if "storageQuotaExceeded" in str(e):
            st.warning("تنبيه: يبدو أن هناك مشكلة في صلاحيات المجلد. تأكد من إضافة إيميل حساب الخدمة كـ 'Editor' للمجلد في Google Drive.")
        return None
