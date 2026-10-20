// Minimal ArkUI control page, compiled directly with the installed SDK es2abc.
class Index extends ViewPU {
    constructor(parent, params, storage, id = -1, paramsLambda, extraInfo) {
        super(parent, storage, id, extraInfo);
        if (this.finalizeConstruction) this.finalizeConstruction();
    }
    setInitiallyProvidedValue(params) {}
    updateStateVars(params) {}
    purgeVariableDependenciesOnElmtId(id) {}
    aboutToBeDeleted() { SubscriberManager.Get().delete(this.id__()); this.aboutToBeDeletedInternal(); }
    initialRender() {
        this.observeComponentCreation2(() => {
            Column.create({space: 20}); Column.width('100%'); Column.height('100%');
            Column.backgroundColor('#fff4f6f8'); Column.padding(30);
        }, Column);
        Column.pop();
    }
    rerender() { this.updateDirtyElements(); }
    static getEntryName() { return 'Index'; }
}
registerNamedRoute(() => new Index(undefined, {}), '', {
    bundleName: 'org.westlake.imehost', moduleName: 'entry', pagePath: 'pages/Index',
    pageFullPath: 'pages/Index', integratedHsp: 'false', moduleType: 'followWithHap'
});
