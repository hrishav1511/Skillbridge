import { ChangeDetectionStrategy, Component } from '@angular/core';
import { LoadingService } from '../../resources/services/loading.service';

@Component({
  selector: 'app-loader',
  templateUrl: './loader.component.html',
  styleUrls: ['./loader.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class LoaderComponent {
  readonly loading$ = this.loadingService.loading$;

  constructor(private loadingService: LoadingService) {}
}