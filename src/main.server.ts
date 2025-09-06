import { bootstrapApplication } from '@angular/platform-browser';
import { App } from './app/app.component';
import { appConfig } from './app/app.config';

const bootstrap = () => bootstrapApplication(App, appConfig)
    .catch((err) => console.error(err));;

export default bootstrap;
