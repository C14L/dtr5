(function(){

let template = document.createElement('template');
let linktpl = document.createElement('template');

template.innerHTML = `
  <style>
    #ul {
    list-style: none;
    margin: 0; padding: 0;
    }
    #ul > li {
    background-color: #888;
    display: inline-block;
    font-size: 0;
    margin: 4px; padding: 0;
    overflow: hidden;
    }
    #ul > li > a {
    border: 0;
    display: inline-block;
    font-size: 1.25rem; line-height: 2.25rem;
    padding: 0 8px;
    text-decoration: inherit;
    color: white;
    }
    #ul > li > a[href^="https://"] {
    border-left: 1px solid gray;
    background-color: rgba(255,255,255,0.28);
    color: white;
    display: inline-block;
    font-size: 1.25rem; line-height: 2.25rem;
    text-shadow: none;
    }
    #ul > li > a[href^="https://"] > span.fa { margin: 0; padding: 0; }
    #ul > li > .banned-tag,
    #ul > li > .muted-tag,
    #ul > li > .mod-tag,
    #ul > li > .nsfw-tag {
    background-color: gray;
    color: white;
    display: inline-block;
    font-size: 1.25rem; line-height: 2.25rem;
    margin: 0; padding: 0 8px;
    }
    #ul > li > .mod-tag {
    background-color: transparent;
    color: red;
    padding-right: 0;
    }
    #ul.smaller > li > a {
    font-size: 1rem; line-height: 2rem;
    }
    #ul.smaller > li > .mod-tag {
    font-size: 1rem; line-height: 2rem;
    }
  </style>
  <ul id="ul"></ul>
`;

linktpl.innerHTML = `
  <li>
    <span class="banned-tag">banned from</span>
    <span class="muted-tag">muted on</span>
    <span class="mod-tag">moderator of</span>
    <a href="{% url 'sr_page' row.sr.display_name %}" 
      title="{{row.sr.subscribers_here|intcomma}} subscribers here"
      >r/{{row.sr.display_name}}</a>
    subscribers here
    <span class="nsfw-tag">NSFW</span>
    
    <a href="https://www.reddit.com/r/{{row.sr.display_name}}" title=" subscribers on reddit"><span class="fa fa-reddit"></span></a>
  </li>
`;

class C14LSrlist extends HTMLElement {

    constructor() {
        super();
        const templateContent = template.content.cloneNode(true);

        this.childNodes.forEach(el => {
            const tpl = linktpl.content.cloneNode(true);

            if (el.hasAttribute('isbanned')) {

            } else
            if (el.hasAttribute('ismuted')) {

            } else
            if (el.hasAttribute('ismod')) {

            } else


        });
    }

    connectedCallback() {
        
    }

    disconnectedCallback() {

    }
}

customElements.define('c14l-srlist', C14LSrlist);

})();