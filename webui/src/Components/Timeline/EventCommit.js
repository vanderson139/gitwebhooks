import React, { Component } from 'react';
import './EventCommit.scss';

class EventCommit extends Component {

  parseId(id) {
    if (id) {
      return id.substring(0, 7);
    }
    return;
  }

  render() {
    if (!this.props.event.commit) {
      return null;
    }

    var commit = this.props.event.commit;

    return (
      <div className={"EventCommit"}>
        <div className="avatar">
            <img alt="Avatar" src={commit.user_avatar_url}></img>
        </div>
        <div className="info">
            <p className="user">{commit.user}</p>
            <p className="commit">
                <a target="_blank" href={commit.url}>{this.parseId(commit.id)}</a>
            </p>
            <p className="message">{commit.message}</p>
        </div>
      </div>
    );
  }
}

export default EventCommit;
