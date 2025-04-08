function getVisibleElementsInViewport() {
    const interactiveElements = [];
    let highlightIndex = 1;
    
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    // Potentially interactive elements
    const elements = document.querySelectorAll(
        'a, button, input, select, textarea, [role="button"], [tabindex="0"]'
    );

    function isInViewport(rect) {
        return (
            rect.width > 0 &&
            rect.height > 0 &&
            rect.bottom >= 0 &&
            rect.right >= 0 &&
            rect.top <= viewportHeight &&
            rect.left <= viewportWidth
        );
    }

    elements.forEach(element => {
        const rect = element.getBoundingClientRect();
        if (isInViewport(rect)) {
            
            // get element attributes
            const attributes = {};
            for (const attr of element.attributes) {
                attributes[attr.name] = attr.value;
            }

            // Get element text content
            let textContent = element.textContent.trim();
            if (element.tagName.toLowerCase() === 'input' && element.value) {
                textContent = element.value;
            }

            // Determine element type
            let elementType = element.tagName.toLowerCase();
            if (element.getAttribute('role')) {
                elementType = element.getAttribute('role');
            }

            interactiveElements.push({
                highlightIndex: highlightIndex++,
                tagName: element.tagName.toLowerCase(),
                type: elementType,
                text: textContent,
                attributes: attributes,
                coordinates: {
                    x: Math.round(rect.left),
                    y: Math.round(rect.top),
                    width: Math.round(rect.width),
                    height: Math.round(rect.height)
                },
                isVisible: true
            });
        }
    });

    return {
        url: window.location.href,
        title: document.title,
        interactiveElements: interactiveElements
    };
}

return getVisibleElementsInViewport();
