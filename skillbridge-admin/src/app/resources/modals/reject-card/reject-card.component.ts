import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { HttpClient } from '@angular/common/http';
import { Component, Inject, OnInit } from '@angular/core';
import { apilists } from '../../ApiList';
import { environment } from 'src/environments/environment';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';

@Component({
  selector: 'app-reject-card',
  templateUrl: './reject-card.component.html',
  styleUrls: ['./reject-card.component.scss']
})
export class RejectCardComponent implements OnInit {
  form!:FormGroup
  constructor(
    private http:HttpClient,
    @Inject(DIALOG_DATA) public data:any,
    private dkialogref:DialogRef<RejectCardComponent>,
    private formBuilder:FormBuilder
  ) { }

  ngOnInit(): void {
    this.form = this.formBuilder.group({
      reason:[null,Validators.required]
    })
  }

  reject(){
    if(this.form.invalid){
      this.form.markAllAsTouched()
      return
    }

    let payload ={
      rejection_reason:this.form.get('reason')?.value
    }
    this.http.post(environment.apiUrl+apilists.approve+this.data.item.id+'/reject/',payload).subscribe({
      next:(res:any)=>{
        this.dkialogref.close()
      },
      error:(err:any)=>{
        console.log(err)
      }
    })
  }

  /**
   * Images and videos attached to the submission.
   *
   * `video_url` is the legacy single-video column and `video_urls` the list;
   * a service can carry either, so both are merged and de-duplicated here.
   */
  get mediaItems(): { type: 'image' | 'video'; url: string }[] {
    const item = this.data?.item || {};
    const images: string[] = Array.isArray(item.image_urls)
      ? item.image_urls.filter((url: string) => !!url)
      : [];
    const videos: string[] = Array.isArray(item.video_urls)
      ? item.video_urls.filter((url: string) => !!url)
      : [];
    if (item.video_url && !videos.includes(item.video_url)) {
      videos.push(item.video_url);
    }
    return [
      ...images.map(url => ({ type: 'image' as const, url })),
      ...videos.map(url => ({ type: 'video' as const, url }))
    ];
  }

  onMediaError(event: Event): void {
    const target = event.target as HTMLElement | null;
    target?.parentElement?.classList.add('media-tile--broken');
  }

  close(){
    this.dkialogref.close()
  }

}
