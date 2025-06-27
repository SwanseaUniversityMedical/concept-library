export const confirmationPrompt = ({ 
  title, 
  content,
  onAccept,
  onRender=null,
  beforeAccept=null,
  onReject=null,
  onError=null
}) => {
  return ModalFactory.create({
    title: title,
    content: content,
    onRender: onRender,
    beforeAccept: beforeAccept
  })
    .then((result) => onAccept(result))
    .catch((e) => {
      if (!!e && !(e instanceof ModalFactory.ModalResults)) {
        if (typeof onError === 'function') {
          return onError();
        }

        return console.error(e);
      }
  
      if (e.name === ModalFactory.ButtonTypes.REJECT) {
        if (typeof onReject === 'function') {
          return onReject();
        }
      }
    });
}
