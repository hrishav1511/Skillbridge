import { Component, Input } from '@angular/core';
import { LoadingState } from '../../models';

@Component({
  selector: 'app-loading',
  templateUrl: './loading.component.html',
  styleUrls: ['./loading.component.scss']
})
export class LoadingComponent {
  // @Input() state: LoadingState | null = LoadingState.IDLE;
  @Input() state: LoadingState | null = LoadingState.IDLE;

  LoadingState = LoadingState;
}
