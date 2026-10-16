import { Dialog } from '@angular/cdk/dialog';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { apilists } from 'src/app/resources/ApiList';
import { ApprovalCardComponent } from 'src/app/resources/modals/approval-card/approval-card.component';
import { RejectCardComponent } from 'src/app/resources/modals/reject-card/reject-card.component';
import { environment } from 'src/environments/environment';

@Component({
  selector: 'app-service-approval',
  templateUrl: './service-approval.component.html',
  styleUrls: ['./service-approval.component.scss']
})
export class ServiceApprovalComponent implements OnInit {
  list: any;

  constructor(private http:HttpClient,private dialog:Dialog){

  }
  ngOnInit(): void {
    this.getData()
  }

  getData(){
    const url = environment.apiUrl + apilists.pending_approval_list
    console.log(url);
    let params:URLSearchParams=new URLSearchParams
    params.set('user_id', JSON.parse(localStorage.getItem('user_id') ?? 'null'))
    this.http.get(url+'?'+params).subscribe({
      next:(res:any)=>{
        this.list = res['data']
        
      }
    })
  }

  approve(item:any){
    const dialogref = this.dialog.open(ApprovalCardComponent,{
      width: '720px',
  maxWidth: '90vw',
  panelClass: 'approval-dialog',
  data:{
    item:item
  }
    })
    dialogref.closed.subscribe((res:any)=>{
      this.getData()
    })
  }

  reject(item:any){
    const dialogref = this.dialog.open(RejectCardComponent,{
      width: '720px',
  maxWidth: '90vw',
  panelClass: 'approval-dialog',
  data:{
    item:item
  }
    })
    dialogref.closed.subscribe((res:any)=>{
      this.getData()
    })
  }
}
