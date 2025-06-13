declare module 'vue-term' {
  import { DefineComponent } from 'vue';

  const VueTerm: DefineComponent<{
    shellWs: WebSocket | null;
    ctlWs: WebSocket | null;
  }>;

  export default VueTerm;
}