#include "session_recovery.h"
#include <atomic>
#include <chrono>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <thread>
#include <sys/stat.h>
#include <unistd.h>
using namespace westlake::recovery;
using namespace westlake::host_window;
static int checks = 0;
#define CHECK(x) do { ++checks; if (!(x)) throw std::runtime_error(#x); } while (0)
static Candidate candidate(int id=62) {
    return Candidate{id, FileIdentity{1,2,100,1,0,1,0,100,100,0660},SourceEvent::WindowReady,{}};
}
struct TestPort : Port {
    ParentReply old{Reply::Missing,-1}, next{Reply::Ok,62};
    Created creation{Reply::Ok,63}; Reply connection=Reply::Ok, disposal=Reply::Ok;
    bool stillCurrent=true;
    bool current() const override { return stillCurrent; }
    int creates=0, connects=0, discards=0, publishes=0, queries=0;
    std::shared_ptr<CallbackGate> oldGate=std::make_shared<CallbackGate>();
    std::function<void()> onCreate, onConnect;
    Routes routes;
    ParentCache parentCache;
    Binding visible{53,53,32,0};
    int windowNode=1, contentNode=2, producer=3, nativeWindow=4, publisher=5;
    const void* resources[5] {&windowNode,&contentNode,&producer,&nativeWindow,&publisher};
    TestPort() { CHECK(routes.install(53,53)); }
    ParentReply parent(int32_t id) override { ++queries; return id==32 ? old : next; }
    Created create(int32_t id,uint64_t generation) override {
        CHECK(id==62); CHECK(generation==1); CHECK(!oldGate->enabled); ++creates;
        if (onCreate) onCreate(); return creation;
    }
    Reply connect(int32_t id) override { CHECK(id==63);++connects;if(onConnect)onConnect();return connection; }
    Reply discard(int32_t id) override { CHECK(id==63);++discards;return disposal; }
    void quiesceOldCallbacks() override { oldGate->close(); }
    bool publish(const Binding& oldBinding,const Binding& nextBinding) override {
        CHECK(oldBinding.logical==53); CHECK(nextBinding.logical==53);
        if(!routes.replace(53,oldBinding.actual,nextBinding.actual)) return false;
        visible=nextBinding;parentCache.publish(nextBinding.parent);++publishes;return true;
    }
};
int main(int argc,char**argv) {
 try {
    CHECK(argc==2);
    auto c=candidate(); std::optional<Observation> observation=Observation{c};
    auto read=[&]{return observation;};
    {
        Coordinator live({53,53,32,0});TestPort p;
        auto pointers=std::vector<const void*>(std::begin(p.resources),std::end(p.resources));
        CHECK(live.poll(1000,read,p)==Outcome::Committed);
        CHECK(live.binding().logical==53 && live.binding().actual==63 && live.binding().parent==62);
        CHECK(p.routes.logical(63)==53);CHECK(p.routes.logical(53)==-1);CHECK(p.routes.logical(777)==777);
        CHECK(p.visible.actual==63);
        CHECK(p.parentCache.committed()==62); // Second window selects new host, not cached32.
        // Production remote operation identity, not Java ID.
        for(size_t i=0;i<pointers.size();++i)CHECK(pointers[i]==p.resources[i]);
        CHECK(live.poll(1500,read,p)==Outcome::Throttled);
        CHECK(live.poll(2000,read,p)==Outcome::Idle);CHECK(p.creates==1);
        int oldCallbacks=0;
        {std::lock_guard<std::recursive_mutex> lock(p.oldGate->mutex);if(p.oldGate->enabled)++oldCallbacks;}
        CHECK(oldCallbacks==0);CHECK(p.visible.actual==63);
        p.routes.erase(53);CHECK(p.routes.logical(63)==-1);
    }
    for (auto stage : {0,3,4,99}) {
        auto hidden=c;hidden.source_event=SourceEvent::StageEvent;hidden.stage_event=stage;
        Coordinator live({53,53,32,0});TestPort p;
        CHECK(!Foreground(hidden));
        CHECK(live.poll(1000,[&]{return std::optional<Observation>{{hidden}};},p)==Outcome::Idle);
        CHECK(p.queries==0 && p.creates==0 && p.connects==0 && p.publishes==0);
    }
    {auto unknown=c;unknown.source_event=SourceEvent::StageEvent;unknown.stage_event.reset();CHECK(!Foreground(unknown));}
    for(auto stage:{1,2}) {auto shown=c;shown.source_event=SourceEvent::StageEvent;shown.stage_event=stage;CHECK(Foreground(shown));}
    {Coordinator live({53,53,62,0});TestPort p;CHECK(live.poll(1000,read,p)==Outcome::Idle);CHECK(p.queries==0);}
    {Coordinator live({53,53,32,0});TestPort p;CHECK(live.poll(1000,[]{return std::optional<Observation>{};},p)==Outcome::Idle);CHECK(!p.creates);}
    for (auto status:{Reply::Ok,Reply::Rejected,Reply::Unknown}) {
        Coordinator live({53,53,32,0});TestPort p;p.old={status,32};
        CHECK(live.poll(1000,read,p)==(status==Reply::Unknown?Outcome::StoppedUnknown:Outcome::Rejected));
        CHECK(p.creates==0);
        CHECK(live.poll(2000,read,p)==(status==Reply::Unknown?Outcome::StoppedUnknown:Outcome::Rejected));
    }
    for (auto status:{Reply::Missing,Reply::Rejected,Reply::Unknown}) {
        Coordinator live({53,53,32,0});TestPort p;p.next={status,-1};
        auto outcome=live.poll(1000,read,p);CHECK(outcome==Outcome::Rejected||outcome==Outcome::StoppedUnknown);CHECK(!p.creates);
    }
    {Coordinator live({53,53,32,0});TestPort p;p.next={Reply::Ok,999};CHECK(live.poll(1000,read,p)==Outcome::Rejected);CHECK(!p.creates);}
    for(auto status:{Reply::Rejected,Reply::Unknown}) {
        Coordinator live({53,53,32,0});TestPort p;p.creation={status,0};
        CHECK(live.poll(1000,read,p)==(status==Reply::Unknown?Outcome::StoppedUnknown:Outcome::Failed));
        CHECK(p.publishes==0&&p.discards==0&&live.binding().actual==53);
        CHECK(live.poll(2000,read,p)==(status==Reply::Unknown?Outcome::StoppedUnknown:Outcome::Idle));CHECK(p.creates==1);
    }
    for(auto status:{Reply::Rejected,Reply::Unknown}) {
        Coordinator live({53,53,32,0});TestPort p;p.connection=status;
        CHECK(live.poll(1000,read,p)==(status==Reply::Unknown?Outcome::StoppedUnknown:Outcome::Failed));
        CHECK(p.publishes==0&&live.binding().actual==53);
        CHECK(p.discards==(status==Reply::Unknown?0:1));
        auto changed=c;changed.file.inode=900;observation=Observation{changed};
        if(status==Reply::Unknown) {CHECK(live.poll(3000,read,p)==Outcome::StoppedUnknown);CHECK(p.creates==1);}
        observation=Observation{c};
    }
    for(int point:{0,1}) {
        Coordinator live({53,53,32,0});TestPort p;
        auto change=[&]{auto hidden=c;hidden.source_event=SourceEvent::StageEvent;hidden.stage_event=4;hidden.file.mtime_nanoseconds++;observation=Observation{hidden};};
        if(point==0)p.onCreate=change;else p.onConnect=change;
        CHECK(live.poll(1000,read,p)==Outcome::Failed);CHECK(p.discards==1&&p.publishes==0);
        CHECK(live.binding().actual==53);observation=Observation{c};
    }
    {Coordinator live({53,53,32,0});TestPort p;p.connection=Reply::Rejected;p.disposal=Reply::Unknown;
     CHECK(live.poll(1000,read,p)==Outcome::StoppedUnknown);CHECK(live.poll(3000,read,p)==Outcome::StoppedUnknown);}
    {Coordinator live({53,53,32,0});TestPort p;
     p.onCreate=[&]{CHECK(live.poll(1001,read,p)==Outcome::InFlight);};
     CHECK(live.poll(1000,read,p)==Outcome::Committed);CHECK(p.creates==1);}
    {Coordinator live({53,53,32,0});TestPort p;
     p.onConnect=[&]{p.stillCurrent=false;};
     CHECK(live.poll(1000,read,p)==Outcome::Failed);CHECK(p.publishes==0&&p.discards==1);}
    {Coordinator live({53,53,32,0});TestPort p;p.old={Reply::Ok,32};
     CHECK(live.poll(1000,read,p)==Outcome::Rejected);CHECK(p.parentCache.committed()==0);
     p.old={Reply::Missing,-1};CHECK(live.poll(2000,read,p)==Outcome::Committed);
     CHECK(p.parentCache.committed()==62);CHECK(p.creates==1);}
    // B1 through Coordinator::poll -> Port::connect -> publication: server
    // callbacks arrive before publication while the real gate buffers them.
    {Coordinator live({53,53,32,0});TestPort p;CallbackGate gate;gate.beginBuffering();
     bool appVisible=false;int width=0;
     p.onConnect=[&]{gate.submit("onNotifySessionForeground", [&]{appVisible=true;});gate.submit("onUpdateRect", [&]{width=1200;});
                    CHECK(!appVisible&&width==0&&p.publishes==0);};
     CHECK(live.poll(1000,read,p)==Outcome::Committed);
     CHECK(!appVisible&&width==0&&p.publishes==1);
     CHECK(Foreground(read()->candidate));CHECK(gate.activate());CHECK(appVisible&&width==1200);}
    // B1 regression: new endpoint receives real lifecycle values during connect.
    // The same production buffering primitive used by SessionStageAdapter must
    // deliver them only after publication, in original order, never synthesize true.
    {CallbackGate gate;gate.beginBuffering();bool visible=false;int rect=0;std::vector<int> order;
     gate.submit("onNotifySessionForeground", [&]{visible=true;order.push_back(1);});
     gate.submit("onUpdateRect", [&]{rect=1200;order.push_back(2);});
     CHECK(!visible&&rect==0);CHECK(gate.pending.size()==2);
     CHECK(gate.activate());CHECK(visible&&rect==1200);CHECK((order==std::vector<int>{1,2}));
     CHECK(gate.activate());CHECK(order.size()==2);
     gate.close();gate.submit("onNotifySessionBackground", [&]{visible=false;});CHECK(visible);CHECK(!gate.activate());}
    // C1: more than64 same-class events while backgrounded do not latch failure.
    {CallbackGate gate;gate.beginBuffering();int callbacks=0,lastWidth=0;
     for(int i=0;i<1000;++i) CHECK(gate.submit("onUpdateRect",[&,i]{++callbacks;lastWidth=i;}));
     CHECK(gate.pending.size()==1);CHECK(!gate.overflow);CHECK(callbacks==0);
     CHECK(gate.activate());CHECK(callbacks==1&&lastWidth==999);}
    // Last-occurrence ordering across methods, not lexical order or first insertion.
    {CallbackGate gate;gate.beginBuffering();bool visible=false;std::vector<int> order;
     for(int i=0;i<100;++i) {
         CHECK(gate.submit("onNotifySessionForeground",[&]{visible=true;order.push_back(1);}));
         CHECK(gate.submit("onNotifySessionBackground",[&]{visible=false;order.push_back(2);}));
     }
     CHECK(gate.pending.size()==2);CHECK(gate.activate());CHECK(!visible);
     CHECK((order==std::vector<int>{1,2}));
     gate.beginBuffering();order.clear();
     CHECK(gate.submit("onNotifySessionBackground",[&]{visible=false;order.push_back(2);}));
     CHECK(gate.submit("onNotifySessionForeground",[&]{visible=true;order.push_back(1);}));
     CHECK(gate.activate());CHECK(visible);CHECK((order==std::vector<int>{2,1}));
     CHECK(!gate.submit("unsupportedFutureCallback",[]{}));}
    // C1 on the production Coordinator connect/publish route, with a delayed activation.
    {Coordinator live({53,53,32,0});TestPort p;CallbackGate gate;gate.beginBuffering();int renderedWidth=0;
     p.onConnect=[&]{for(int i=1;i<=100;++i)gate.submit("onUpdateRect",[&,i]{renderedWidth=i;});};
     CHECK(live.poll(1000,read,p)==Outcome::Committed);CHECK(renderedWidth==0);
     CHECK(gate.activate());CHECK(renderedWidth==100);}
    // Gate close must drain an admitted callback, not just compare a generation once.
    {CallbackGate gate;std::atomic<bool> entered{false}, release{false}, closed{false};
     std::thread callback([&]{std::lock_guard<std::recursive_mutex> g(gate.mutex);entered=true;
         while(!release.load())std::this_thread::yield();});
     while(!entered.load())std::this_thread::yield();
     std::thread closer([&]{gate.close();closed=true;});
     std::this_thread::sleep_for(std::chrono::milliseconds(5));CHECK(!closed.load());
     release=true;callback.join();closer.join();CHECK(closed.load()&&!gate.enabled);}
    // Real t1 production parser + reader are linked, not a fake authorization predicate.
    std::string path=std::string(argv[1])+"/record.json";
    auto write=[&](const char* body){std::ofstream out(path);out<<body;out.close();chmod(path.c_str(),0660);};
    write("{\"event\":\"stage-event\",\"details\":{\"event\":4,\"window\":{\"id\":62}}}");
    auto hidden=ReadObservation(path,getuid(),getgid());CHECK(hidden && !Foreground(hidden->candidate));
    {Coordinator live({53,53,32,0});TestPort p;CHECK(live.poll(1000,[&]{return ReadObservation(path,getuid(),getgid());},p)==Outcome::Idle);CHECK(!p.creates);}
    write("{\"event\":\"window-ready\",\"details\":{\"id\":62}}");
    auto ready=ReadObservation(path,getuid(),getgid());CHECK(ready && Foreground(ready->candidate));
    CHECK(!ReadObservation(path,getuid()+1,getgid()));
    write("{\"event\":\"stage-event\",\"details\":{\"window\":{\"id\":62}}}");
    auto absent=ReadObservation(path,getuid(),getgid());CHECK(absent&&!Foreground(absent->candidate));
    std::cout<<"{\"assertions\":"<<checks<<",\"status\":\"passed\"}\n";
 }catch(const std::exception& e){std::cerr<<"FAILED after "<<checks<<": "<<e.what()<<"\n";return 1;}
}
