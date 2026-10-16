import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { HttpClient } from '@angular/common/http';
import { Component, Inject, OnInit } from '@angular/core';
import { environment } from 'src/environments/environment';
import { apilists } from '../../ApiList';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';

@Component({
  selector: 'app-user-action',
  templateUrl: './user-action.component.html',
  styleUrls: ['./user-action.component.scss']
})
export class UserActionComponent implements OnInit {
  form!:FormGroup
  constructor(
    @Inject(DIALOG_DATA) public data: any,
    private dialogRef:DialogRef<UserActionComponent>,
    private http:HttpClient,
    private fb:FormBuilder
  ) { }

  ngOnInit(): void {
    if(this.data.action=='REJECT'){
      this.form = this.fb.group({
        reason: [null, Validators.required]
      });
    }
    console.log(this.data.action);
    
  }

  formatModerationLabel(key: string): string {
    const labels: Record<string, string> = {
      insult: 'Insult',
      threat: 'Threat',
      obscene: 'Obscene',
      toxicity: 'Toxicity',
      identity_attack: 'Identity Attack',
      severe_toxicity: 'Severe Toxicity',
      sexual_explicit: 'Sexually Explicit'
    };

    return labels[key] || key.replace(/_/g, ' ');
  }

  approve(){
    let params:URLSearchParams=new URLSearchParams
    params.set('user_id', JSON.parse(localStorage.getItem('user_id') ?? 'null'))
    this.http.post(environment.apiUrl+ apilists.pending_user_action + this.data.item.id + '/approve/?'+params ,{}).subscribe({
      next:(res:any)=>{
        this.dialogRef.close()
      }
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
    this.http.post(environment.apiUrl+apilists.pending_user_action+this.data.item.id+'/reject/',payload).subscribe({
      next:(res:any)=>{
        this.dialogRef.close()
      },
      error:(err:any)=>{
        console.log(err)
      }
    })
  }

  close(){
    this.dialogRef.close()
  }
}
