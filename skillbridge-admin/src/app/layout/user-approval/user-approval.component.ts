import { Dialog } from '@angular/cdk/dialog';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { apilists } from 'src/app/resources/ApiList';
import { UserActionComponent } from 'src/app/resources/modals/user-action/user-action.component';
import { environment } from 'src/environments/environment';

@Component({
  selector: 'app-user-approval',
  templateUrl: './user-approval.component.html',
  styleUrls: ['./user-approval.component.scss']
})
export class UserApprovalComponent implements OnInit {
  list: any;

  constructor(private http:HttpClient,
    private dialog:Dialog
  ){

  }
  ngOnInit(): void {
    this.getData()
  }

  getData(){
    const url = environment.apiUrl + apilists.pending_user
    console.log(url);
    let params:URLSearchParams=new URLSearchParams
    params.set('user_id', JSON.parse(localStorage.getItem('user_id') ?? 'null'))
    // params.set('approval_status','PENDING')
    this.http.get(url+'?'+params).subscribe({
      next:(res:any)=>{
        console.log(res);
        this.list = res['data']
        
      }
    })
  }

  approve(item:any){
   const dialogRef = this.dialog.open(UserActionComponent,{
    width:'720px',
    maxWidth:'90vw',
    data:{
      action:'APPROVE',
      item:item,
    }
  })
  dialogRef.closed.subscribe((res:any)=>{
      this.getData()
    
})
}

reject(item:any){
  const dialogRef = this.dialog.open(UserActionComponent,{
    width:'720px',
    maxWidth:'90vw',
    data:{
      action:'REJECT',
      item:item,
    }
  })
  dialogRef.closed.subscribe((res:any)=>{
      this.getData()
  })}
}
