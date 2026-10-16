import { HttpClient } from '@angular/common/http';
import { Component, Inject } from '@angular/core';
import { environment } from 'src/environments/environment';
import { apilists } from '../../ApiList';
import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';

@Component({
  selector: 'app-approval-card',
  templateUrl: './approval-card.component.html',
  styleUrls: ['./approval-card.component.scss']
})
export class ApprovalCardComponent  {


  constructor(private http:HttpClient,
    @Inject(DIALOG_DATA) public data:any,
    private dkialogref:DialogRef<ApprovalCardComponent>
  ){
    console.log(data.item)
  }

  approve(){
    let params:URLSearchParams = new URLSearchParams
    params.set('user_id',JSON.parse(localStorage.getItem('user_id') ?? 'null'))
    this.http.post(environment.apiUrl+apilists.approve+this.data.item.id+'/approve/'+'?'+params,{}).subscribe({
      next:(res:any)=>{
        this.dkialogref.close()
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
