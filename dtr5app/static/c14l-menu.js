(function(){
  let template = document.createElement('template');
  template.innerHTML = `
    <style>
      nav {
        color: gray;
        cursor: pointer;
        display: block;
        width: 2.5rem;
        height: 2.5rem;
        float: right;
        font-weight: normal;
        font-style: normal;
        font-size: 2.5rem;
        line-height: 2.5rem;
        opacity: 1;
        padding: 0; margin: 0;
        position: relative;
        text-align: center;
      }
      nav:hover {
        transform: 0.1s;
      }
      #activator {
        background: blue;
        cursor: pointer;
        display: inline-block;
        position: absolute;
        top: 0; bottom: 0; left: 0; right: 0;
      }
      #activator::before {
        content: '';
        background: green;
        border-radius: 50%;
        width: 1rem; 
        height: 1rem;
        position: absolute;
        top: calc(50% - 0.5rem);
        left: calc(50% - 0.5rem);
      }
      #ul {
        background-color: #fff;
        border-radius: 2px;
        box-shadow: 0 1px 6px 0 rgba(0,0,0,0.6);
        color: rgba(0,0,0,1);
        display: none;
        font-size: 1rem;
        line-height: 1rem;
        list-style: none;
        margin: 0; padding: 0;
        min-height: 1rem;
        overflow: hidden;
        position: absolute;
        right: 8px;
        text-align: left;
        top: 32px;
        width: 250px;
        z-index: 50;
      }
      #ul.isopen {
        display: block;
      }
      #ul > li {
        border-top: 1px solid #ccc;
        margin: 0; padding: 0;
        transition: 0.1s ease-in;
      }
      #ul > li:hover {
        background-color: #F3F3F3;
        transition: 0.1s ease-out;
      }
      #ul > li:first-child {
        border-top: 0;
      }
      #ul > li > form,
      #ul > li > span,
      #ul > li > a {
        background: transparent;
        border: 0;
        color: inherit;
        cursor: pointer;
        display: block;
        font-weight: normal;
        font-size: inherit;
        line-height: inherit;
        margin: 0 0 0 1.75rem;
        padding: 1rem;
        text-align: left;
        text-decoration: inherit;
      }
      #ul > li > span.secondary,
      #ul > li > a.secondary {
        color: gray;
      }
    </style>
    <nav>
      <div id="activator"></div>
      <ul id="ul"><li></li></ul>
    </nav>
  `;

  class C14LMenu extends HTMLElement {

    constructor() {
      super();
      const templateContent = template.content.cloneNode(true);
      const activator = templateContent.getElementById('activator');
      const ul = templateContent.getElementById('ul');
      const wrap = ul.childNodes[0];
      ul.classList.remove('isopen');
      ul.removeChild(wrap);

      this.childNodes.forEach(el => {
        let li = wrap.cloneNode(true);
        li.appendChild(el.cloneNode(true));
        ul.appendChild(li);
      });

      window.addEventListener('click', (event) => {
        if (event.target != this) ul.classList.remove('isopen');
      });

      activator.addEventListener('click', (event) => {
        event.stopPropagation();
        ul.classList.toggle('isopen');
      });

      const shadowRoot = this.attachShadow({mode: 'open'});
      shadowRoot.appendChild(templateContent);
    }
    
    connectedCallback () {}
    disconnectedCallback () {}
  }

  window.customElements.define('c14l-menu', C14LMenu);
})();
