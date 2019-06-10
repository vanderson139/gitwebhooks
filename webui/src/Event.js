import moment from 'moment';

class Event {

  constructor(event) {
    var self = this;
    self.event = event;

    for(var key in event) {
        if(!event.hasOwnProperty(key))
            continue;
        self[key] = event[key];
    }
  }

  getColorClass() {

      if(this.event.type === "StartupEvent")
        return "purple";

      if(this.event.type === "WebhookAction")
        return "blue";

      if(this.event.type === "DeployEvent")
        return "green";

      return "purple";
  }

  getTitle() {

      if(this.event.type === "StartupEvent")
        return "Startup";

      if(this.event.type === "WebhookAction")
        return "Webhook";

      if(this.event.type === "DeployEvent")
        return "Deploy";

      return this.event.type;
  }

  getSubtitle() {

      if(this.event.type === "StartupEvent") {

        if(this.isWaiting())
          return "Inicializando...";

        return "Escutando novas conexões";
      }

      if(this.event.type === "WebhookAction") {
        if(this.event.messages.length)
          return this.event.messages[this.event.messages.length - 1].message;

        return "Solicitação recebida de " + this.event['client-address'];
      }

      if(this.event.type === "DeployEvent")
        return this.event.name;

      return this.event.type;
  }

  getDate() {
      return moment.unix(this.event.timestamp).format("DD/MM/YYYY");
  }

  getTime() {
      return moment.unix(this.event.timestamp).format("HH:mm");
  }

  getIconName() {

    if(this.event.success === false)
      return "alert";

    if(this.event.type === "StartupEvent")
      return "alert-circle";

    return "check";
  }

  isWaiting() {
    return this.event.waiting;
  }
}

export default Event;
