import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { HttpClient } from '@angular/common/http';
import { Component, Inject, OnInit } from '@angular/core';
import { apiLists } from '../../apiLists';
import { environment } from '../../../../environments/environment.prod';
import { ToastrService } from 'ngx-toastr';

@Component({
  selector: 'app-attachmentts',
  templateUrl: './attachmentts.component.html',
  styleUrls: ['./attachmentts.component.scss']
})
export class AttachmenttsComponent implements OnInit {
  attchment_url:string = ''
  constructor(
    @Inject(DIALOG_DATA) public data: any,
    private dialogRef: DialogRef<AttachmenttsComponent>,
    private http: HttpClient,
    private toastr:ToastrService
  ) { 
    this.attchment_url =environment.apiUrl + apiLists.attachment_list_upload+ this.data.service.id+'/attachments/'
  }

  ngOnInit(): void {
    console.log(this.data)
    this.getAttachments()
  }

  getAttachments(){
    this.http.get<any>(this.attchment_url).subscribe({
      next: (response) => {
        this.data.attachments = response?.data
      },
      error:(error:any)=>{
        console.error('Error fetching attachments:', error);
      }
  })}

  uploadAttachment(event:any){
    const file: File = event.target.files[0];
    if (file) {
      const formData = new FormData();
      formData.append('file', file);
      this.http.post<any>(this.attchment_url, formData).subscribe({
        next: (response) => {
          this.toastr.success('Attachment uploaded successfully!');
          this.getAttachments()
        },
        error: (error) => {
          this.toastr.error(error.error.detail || 'Error uploading attachment');
          console.error('Error uploading attachment:', error);
        }
      });
    }
  }

  close(){
    this.dialogRef.close()
  }

}
