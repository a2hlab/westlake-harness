#include "../jni/direct_surface_path_tracker.h"

#include <cassert>
#include <cstring>

using Tracker = oh_adapter::DirectSurfacePathTracker;

static void testFirstAndContinuousFrames()
{
    Tracker tracker;
    assert(tracker.bind(Tracker::Route::DIRECT, 41, 1, 7001, 1280, 720) ==
           Tracker::Result::OK);
    assert(tracker.bind(Tracker::Route::DIRECT, 41, 1, 7999, 1280, 720) ==
           Tracker::Result::INVALID_ARGUMENT);
    assert(tracker.recordQueue(1, 1, 100) == Tracker::Result::OK);
    assert(tracker.recordPresent(1, 1, 120) == Tracker::Result::OK);
    assert(tracker.recordQueue(1, 2, 200) == Tracker::Result::OK);
    assert(tracker.recordPresent(1, 2, 230) == Tracker::Result::OK);
    assert(tracker.snapshot().queuedFrames == 2);
    assert(tracker.snapshot().presentedFrames == 2);
    assert(tracker.snapshot().firstQueueNs == 100);
}

static void testResizeAndRotationGeometry()
{
    Tracker tracker;
    assert(tracker.bind(Tracker::Route::DIRECT, 42, 3, 7002, 1280, 720) ==
           Tracker::Result::OK);
    assert(tracker.resize(3, 720, 1280) == Tracker::Result::OK);
    assert(tracker.snapshot().width == 720);
    assert(tracker.snapshot().height == 1280);
    assert(tracker.snapshot().resizeCount == 1);
    assert(tracker.resize(3, 0, 1280) == Tracker::Result::INVALID_ARGUMENT);
}

static void testSurfaceLossRejectsOldGenerationAndRecovers()
{
    Tracker tracker;
    assert(tracker.bind(Tracker::Route::DIRECT, 43, 9, 7003, 800, 600) ==
           Tracker::Result::OK);
    assert(tracker.recordQueue(9, 1, 100) == Tracker::Result::OK);
    assert(tracker.markLost(9) == Tracker::Result::OK);
    assert(tracker.recordQueue(9, 2, 200) == Tracker::Result::SURFACE_LOST);
    assert(tracker.bind(Tracker::Route::DIRECT, 43, 10, 7004, 600, 800) ==
           Tracker::Result::OK);
    assert(tracker.recordQueue(9, 2, 210) == Tracker::Result::STALE_GENERATION);
    assert(tracker.recordQueue(10, 1, 220) == Tracker::Result::OK);
    assert(tracker.snapshot().generation == 10);
    assert(tracker.snapshot().surfaceId == 7004);
}

static void testDirectBrokerMeasurementSchemaWithoutBrokerTopology()
{
    assert(std::strcmp(Tracker::routeName(Tracker::Route::DIRECT), "direct") == 0);
    assert(std::strcmp(Tracker::routeName(Tracker::Route::BROKER), "broker") == 0);
    Tracker brokerSample;
    assert(brokerSample.bind(Tracker::Route::BROKER, 99, 1, 8001, 64, 64) ==
           Tracker::Result::OK);
    assert(brokerSample.snapshot().route == Tracker::Route::BROKER);
    // This proves only that paired samples share one schema.  It does not
    // instantiate or select a broker implementation.
}

int main()
{
    testFirstAndContinuousFrames();
    testResizeAndRotationGeometry();
    testSurfaceLossRejectsOldGenerationAndRecovers();
    testDirectBrokerMeasurementSchemaWithoutBrokerTopology();
    return 0;
}
