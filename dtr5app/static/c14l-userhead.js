(function(){
    let template = document.createElement('template');
    template.innerHTML = `
        <style>
            #pics-state {
                width: 0px;
                height: 0px;
                opacity: 0;
            }
            #pics-state + #pics {
                background: transparent;
                cursor: pointer;
                display: block;
                height: 280px;
                margin: 32px 0;
                padding: 0;
                position: relative;
                width: 280px;
            }
            #pics-state + #pics div {
                background-position: center center;
                background-repeat: no-repeat;
                background-size: cover;
                border: 0;
                display: inline-block;
                height: 280px;
                left: 0;
                position: absolute;
                top: 0;
                transition: 0.15s ease-out;
                width: 280px;
            }
            #pics-state:checked + #pics {
            }
            #pics-state:checked + #pics div {
                box-shadow: 0 0 40px rgba(0,0,0,0.75);
            }
            #pics-state:checked + #pics div:nth-child(1) {
                left: 0;
                transform: rotate(-5deg);
            }
            #pics-state:checked + #pics div:nth-child(2) {
                left: calc(1 * 280px);
                transform: rotate(2deg);
            }
            #pics-state:checked + #pics div:nth-child(3) {
                left: calc(2 * 280px);
                transform: rotate(10deg);
            }
        </style>
        <input type="checkbox" id="pics-state">
        <label for="pics-state" id="pics"></label>
    `;

    class C14LUserHead extends HTMLElement {

        constructor() {
            super();
            const templateContent = template.content.cloneNode(true);
            const picsEl = templateContent.getElementById('pics');

            this.getAttribute('pics').split(' ').filter(x => x).reverse().forEach(url => {
                const div = document.createElement('div');
                div.style.backgroundImage = `url(${url})`;
                picsEl.appendChild(div);
            });

            const shadowRoot = this.attachShadow({mode: 'open'});
            shadowRoot.appendChild(templateContent);
        }

        connectedCallback () {

        }

        disconnectedCallback () {

        }
    }

    window.customElements.define('c14l-userhead', C14LUserHead);
  })();
