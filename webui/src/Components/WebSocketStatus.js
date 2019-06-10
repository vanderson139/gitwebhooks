import React, { Component } from 'react';
import './WebSocketStatus.scss';

class WebSocketStatus extends Component {

  render() {

    if(this.props.wsIsOpen && !this.props.wsIsAuthenticated)
      return (
        <div className="WebSocketStatus">
          <span className="status authenticating"
             title={"Autenticando em " + this.props.wsURI}>
          </span>
          <span className="pulse"></span>
        </div>
      );

    if(this.props.wsIsRecovering)
      return (
        <div className="WebSocketStatus">
          <span className="status reconnecting"
             title={"Reconectando em " + this.props.wsURI}>
          </span>
          <span className="pulse"></span>
        </div>
      );

    if(this.props.wsIsOpen)
      return (
        <div className="WebSocketStatus">
          <span className="status connected"
             title={"Recebendo atualizações em tempo real de " + this.props.wsURI}>
          </span>
        </div>
      );

    if (document.readyState === "complete")
      return (
          <div className="WebSocketStatus">
             <span className="status"
               title="Desconectado">
            </span>
          </div>
        );

    return;
  }
}

export default WebSocketStatus;
