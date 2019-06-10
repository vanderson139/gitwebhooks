import React, { Component } from 'react';
import './EventMessages.scss';

class EventMessages extends Component {

  getMessages() {
    
    var messages = this.props.event.messages;

    if(!messages)
      return;
    
    var elements = [];

    messages.forEach(function(message, index) {
      elements.push(
        <p key={index}>
          <span className={message.status}></span>
          {message.message}
        </p>);
    });

    return elements;
  }

  render() {
    return (
      <div className={"EventMessages"}>
            {this.getMessages()}
      </div>
    );
  }
}

export default EventMessages;
