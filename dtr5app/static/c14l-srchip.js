(function(){

    class C14LSrchip extends HTMLAnchorElement {

        constructor() {
            super();

            const span = document.createElement('span');
            span.classList.add('sr-name');
            span.innerText = 'r/' + this.innerText;
            span.style.backgroundColor = 'green';
            span.style.borderRadius = '5px';
            span.style.color = 'white';
            span.style.display = 'inline-block';
            span.style.fontSize = '0.8rem';
            span.style.fontWeight = 'bold';
            span.style.lineHeight = '2rem';
            span.style.padding = '0 0.5rem';
            span.style.margin = '0.25rem';

            if (this.hasAttribute('isbanned')) {
                // span.prepend(this._get_span('banned-tag', "banned from"));
            } else
            if (this.hasAttribute('ismuted')) {
                // span.prepend(this._get_span('muted-tag', "muted on"));
            } else
            if (this.hasAttribute('ismod')) {
                span.style.backgroundColor = 'yellow';
                span.style.color = 'red';
                span.title = 'moderator of this subreddit';
            } else
            if (this.hasAttribute('isnsfw')) {
                // span.append(this._get_span('nsfw-tag', "NSFW"));
            }

            this.innerText = '';
            this.prepend(span);
        }
    
        connectedCallback() {
        }

        disconnectedCallback() {
        }

        _get_span(cls, text) {
            const span = document.createElement('span');
            span.classList.add(cls);
            span.innerText = text;
            return span;
        }
    }

    customElements.define('c14l-srchip', C14LSrchip, {"extends": "a"});
})();